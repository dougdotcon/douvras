"""O caminho de interpretação, exercitado com entrada não-degenerada.

Com o corpus real, `build_candidates` devolve lista vazia, `score` devolve `CSSResult()` e todo
o ramo de interpretação do Atlas — déficit, ranking, sensibilidade, discriminação, alvo — passa
o ciclo inteiro sem executar uma linha útil. Uma suíte que só rode o corpus real fica verde com
a fórmula do CSS trocada por outra errada.

Estes testes existem para que a próxima pessoa que mexer no CSS descubra na hora.
"""

from __future__ import annotations

import numpy as np
import pytest

from douvras_core.status import Status
from model_atlas import css as css_mod
from model_atlas.capability import CapabilityFingerprint, GAP_NO_EXECUTION
from model_atlas.tasks import Capability


def test_a_fixture_e_de_fato_nao_degenerada(fingerprint_medido, priors) -> None:
    """Se a fixture degenerar, todos os testes abaixo passam por vacuidade."""
    cand = css_mod.build_candidates(fingerprint_medido, priors)
    assert len(cand) == 8, "menos de oito candidatos: o caminho nao esta sendo exercitado"
    deficits = sorted(c.deficit for c in cand)
    assert deficits[-1] - deficits[0] > 0.5, "deficits achatados nao testam discriminacao"


def test_deficit_e_o_complemento_do_escore(fingerprint_medido, priors) -> None:
    cand = {c.capability: c for c in css_mod.build_candidates(fingerprint_medido, priors)}
    assert cand[Capability.HALLUCINATION].deficit == pytest.approx(0.82)
    assert cand[Capability.STRUCTURED_OUTPUT].deficit == pytest.approx(0.05)


def test_o_ranking_ordena_do_maior_para_o_menor(fingerprint_medido, priors, pesos) -> None:
    r = css_mod.score(css_mod.build_candidates(fingerprint_medido, priors), pesos)
    valores = [v for _, v in r.ranking]
    assert valores == sorted(valores, reverse=True)
    assert r.leader == r.ranking[0][0]


def test_o_css_e_monotonico_no_deficit(fingerprint_medido, priors, pesos) -> None:
    """Piorar uma capacidade não pode reduzir sua pontuação como candidata a dataset.

    É a mesma classe de defeito que o `energy_gain` anti-monotônico do Silicon Atlas, onde
    endurecer nada pontuava mais que endurecer 99,5 %.
    """
    antes = dict(css_mod.score(css_mod.build_candidates(fingerprint_medido, priors), pesos).ranking)

    from douvras_core.status import Finding

    pior = CapabilityFingerprint(model_id="pior", measured=True)
    pior.scores = dict(fingerprint_medido.scores)
    pior.scores[Capability.PLANNING] = Finding(
        "capacidade.planning", 0.05, Status.OBSERVATION
    )
    depois = dict(css_mod.score(css_mod.build_candidates(pior, priors), pesos).ranking)

    assert depois[Capability.PLANNING] > antes[Capability.PLANNING]


def test_sensibilidade_roda_e_produz_margem_e_ruido(fingerprint_medido, priors, pesos) -> None:
    r = css_mod.score(css_mod.build_candidates(fingerprint_medido, priors), pesos)
    assert r.samples > 0
    assert r.weight_noise > 0.0, "ruido zero significa que a perturbacao nao rodou"
    assert 0.0 <= r.top1_stability <= 1.0


def test_discriminacao_compara_margem_com_ruido_e_nao_so_estabilidade(
    fingerprint_medido, priors, pesos
) -> None:
    """A lição do `CE-001`: ranking perfeitamente estável e margem menor que o ruído convivem.

    Um `discriminates` que olhasse só `top1_stability` diria "sim" para o caso em que o líder
    vence por menos que o desvio dos próprios pesos — que foi exatamente o erro retratado no
    Silicon Atlas.
    """
    r = css_mod.score(css_mod.build_candidates(fingerprint_medido, priors), pesos)
    assert r.discriminates == (r.leader_margin > r.weight_noise)

    achatado = css_mod.CSSResult(
        ranking=[(Capability.PLANNING, 0.5000), (Capability.ARGUMENTS, 0.4999)],
        top1_stability=1.0,
        leader_margin=0.0001,
        weight_noise=0.02,
        samples=4000,
    )
    assert achatado.top1_stability == 1.0
    assert not achatado.discriminates


def test_o_css_e_deterministico_sob_a_mesma_semente(fingerprint_medido, priors, pesos) -> None:
    cand = css_mod.build_candidates(fingerprint_medido, priors)
    a = css_mod.score(cand, pesos)
    b = css_mod.score(cand, pesos)
    assert a.as_dict() == b.as_dict()


def test_com_medicao_o_finding_de_css_carrega_a_lacuna_dos_priors(
    fingerprint_medido, priors, pesos
) -> None:
    """Mesmo medido, o CSS não passa de `CONDITIONAL_RESULT`: os priors continuam abertos."""
    r = css_mod.score(css_mod.build_candidates(fingerprint_medido, priors), pesos)
    f = css_mod.css_finding(fingerprint_medido, r)
    assert "G-104" in f.gaps
    assert f.status <= Status.CONDITIONAL_RESULT


def test_sem_medicao_o_css_e_ausencia_declarada_e_nao_zero(priors, pesos) -> None:
    fp = CapabilityFingerprint.unmeasured("sem-pesos", list(Capability))
    cand = css_mod.build_candidates(fp, priors)
    assert cand == []
    f = css_mod.css_finding(fp, css_mod.score(cand, pesos))
    assert f.value is None
    assert f.status is Status.OPEN_GAP
    assert GAP_NO_EXECUTION in f.gaps


def test_pesos_normalizam_e_perturbacao_respeita_o_intervalo(pesos) -> None:
    v = pesos.vector(list(css_mod.CapabilityCandidate.FACTOR_KEYS))
    assert np.all(v > 0)
    assert pesos.perturbation == pytest.approx(0.20)
