from array import array

import pytest

from agent.voix_conseil import OCTETS_PAR_SECONDE, TAUX, PriseImpossible, decouper, silences


def _son(*morceaux):
    """(durée, parle ?) -> PCM : un signal fort quand on parle, zéro sinon."""
    ech = array("h")
    for duree, parle in morceaux:
        n = int(duree * TAUX)
        ech.extend([8000 if k % 2 else -8000 for k in range(n)] if parle else [0] * n)
    return ech.tobytes()


def test_silences_repere_les_vraies_pauses():
    trouves = silences(_son((1, True), (0.5, False), (1, True), (0.05, False), (1, True)))
    assert len(trouves) == 1
    assert trouves[0][0] == pytest.approx(1, abs=0.03) and trouves[0][1] == pytest.approx(1.5, abs=0.03)


def test_decouper_coupe_dans_les_silences_entre_scenes():
    pcm = _son((3, True), (0.6, False), (1, True), (0.15, False), (1, True), (0.6, False), (2, True))
    a, b, c = decouper(pcm, [300, 200, 200])
    assert b"".join((a, b, c)) == pcm
    assert len(a) / OCTETS_PAR_SECONDE == pytest.approx(3.3, abs=0.05)
    assert len(c) / OCTETS_PAR_SECONDE == pytest.approx(2.3, abs=0.05)


def test_decouper_sans_assez_de_silences_refuse():
    with pytest.raises(PriseImpossible):
        decouper(_son((3, True)), [100, 100])


def test_une_seule_scene_reste_entiere():
    pcm = _son((1, True))
    assert decouper(pcm, [100]) == [pcm]
