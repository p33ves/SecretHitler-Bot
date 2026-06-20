import pytest
from secret_hitler.policy_pile import Policy, PolicyPile, PolicyError


class TestPolicyEnum:
    @pytest.mark.parametrize("token", ["fascist", "red", "r", "RED", "R", "Fascist"])
    def test_get_enum_fascist_variants(self, token):
        assert Policy.getEnum(token) == Policy.Fascist

    @pytest.mark.parametrize("token", ["liberal", "blue", "b", "BLUE", "B", "Liberal"])
    def test_get_enum_liberal_variants(self, token):
        assert Policy.getEnum(token) == Policy.Liberal

    @pytest.mark.parametrize("token", ["green", "yellow", "", "123"])
    def test_get_enum_invalid_returns_none(self, token):
        assert Policy.getEnum(token) is None


class TestPolicyPile:
    def test_initial_deck_has_17_cards(self):
        pile = PolicyPile()
        assert pile.noOfCardsInDeck == 17

    def test_initial_deck_composition(self):
        pile = PolicyPile()
        fascist = sum(1 for _ in range(pile.noOfCardsInDeck) if pile.peekTop3())
        # Verify composition via peek across all cards
        all_cards = pile.peekTop3() + pile._PolicyPile__drawPile[3:]
        assert all_cards.count(Policy.Fascist) == 11
        assert all_cards.count(Policy.Liberal) == 6

    def test_draw_takes_3_cards_from_deck(self):
        pile = PolicyPile()
        pile.draw()
        assert len(pile.cardsInPlay) == 3
        assert pile.noOfCardsInDeck == 14

    def test_draw_raises_when_cards_already_in_play(self):
        pile = PolicyPile()
        pile.draw()
        with pytest.raises(PolicyError):
            pile.draw()

    def test_discard_removes_one_card_from_hand(self):
        pile = PolicyPile()
        pile.draw()
        card = pile.cardsInPlay[0]
        pile.discardPolicy(card)
        assert len(pile.cardsInPlay) == 2

    def test_discard_raises_when_hand_not_3_cards(self):
        pile = PolicyPile()
        pile.draw()
        pile.discardPolicy(pile.cardsInPlay[0])
        # hand now has 2 — discardPolicy requires exactly 3
        with pytest.raises(PolicyError):
            pile.discardPolicy(pile.cardsInPlay[0])

    def test_discard_raises_for_card_not_in_hand(self):
        pile = PolicyPile()
        # Force a hand of all-Fascist by manipulating the draw pile
        pile._PolicyPile__drawPile = [Policy.Fascist] * 3 + pile._PolicyPile__drawPile
        pile.draw()
        with pytest.raises(PolicyError):
            pile.discardPolicy(Policy.Liberal)

    def test_accept_policy_clears_hand(self):
        pile = PolicyPile()
        pile.draw()
        pile.discardPolicy(pile.cardsInPlay[0])
        card = pile.cardsInPlay[0]
        pile.acceptPolicy(card)
        assert len(pile.cardsInPlay) == 0

    def test_accept_policy_raises_when_hand_not_2_cards(self):
        pile = PolicyPile()
        pile.draw()
        # hand has 3 — acceptPolicy requires exactly 2
        with pytest.raises(PolicyError):
            pile.acceptPolicy(pile.cardsInPlay[0])

    def test_accept_policy_remaining_card_enters_discard(self):
        """Regression: old code did append(list) instead of extend(list),
        silently corrupting the discard pile so the next reshuffle broke."""
        pile = PolicyPile()
        # Drain the draw pile so a reshuffle is forced after the first cycle
        while pile.noOfCardsInDeck >= 3:
            pile.draw()
            pile.discardPolicy(pile.cardsInPlay[0])
            pile.acceptPolicy(pile.cardsInPlay[0])
        # If acceptPolicy was broken, extend() on a list-of-lists would raise
        shuffled = pile.draw()
        assert shuffled is True
        assert len(pile.cardsInPlay) == 3

    def test_peek_top3_does_not_consume_cards(self):
        pile = PolicyPile()
        before = pile.noOfCardsInDeck
        top3 = pile.peekTop3()
        assert len(top3) == 3
        assert pile.noOfCardsInDeck == before

    def test_place_top_policy_removes_top_card(self):
        pile = PolicyPile()
        expected = pile.peekTop3()[0]
        placed = pile.placeTopPolicy()
        assert placed == expected
        assert pile.noOfCardsInDeck == 16

    def test_reshuffle_triggered_when_deck_runs_below_3(self):
        pile = PolicyPile()
        while pile.noOfCardsInDeck >= 3:
            pile.draw()
            pile.discardPolicy(pile.cardsInPlay[0])
            pile.acceptPolicy(pile.cardsInPlay[0])
        assert pile.noOfCardsInDeck < 3
        shuffled = pile.draw()
        assert shuffled is True

    def test_reshuffle_merges_discard_into_draw(self):
        pile = PolicyPile()
        # One full cycle: 3 drawn, 1 enacted (gone), 2 back to discard
        pile.draw()
        pile.discardPolicy(pile.cardsInPlay[0])
        pile.acceptPolicy(pile.cardsInPlay[0])
        # Exhaust remaining draw pile
        while pile.noOfCardsInDeck >= 3:
            pile.draw()
            pile.discardPolicy(pile.cardsInPlay[0])
            pile.acceptPolicy(pile.cardsInPlay[0])
        deck_before_shuffle = pile.noOfCardsInDeck
        shuffled = pile.draw()
        assert shuffled is True
        # After reshuffle, total in draw + in play should be > deck_before_shuffle
        assert pile.noOfCardsInDeck + len(pile.cardsInPlay) > deck_before_shuffle
