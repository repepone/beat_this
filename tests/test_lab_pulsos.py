from lab_pulsos.pulsos import a_lista, corregir_con_anclas, estimar_cifras


def compas(n_compases, por_compas, periodo=0.5, t0=0.5):
    n = n_compases * por_compas
    return [{"t": t0 + i * periodo, "fuerte": i % por_compas == 0} for i in range(n)]


def test_a_lista_une_fuertes():
    lista = a_lista([0.5, 1.0, 1.5, 2.0], [0.51, 2.0])
    assert [p["fuerte"] for p in lista] == [True, False, False, True]


def test_cifras_con_cambio():
    pulsos = compas(4, 4)
    t = pulsos[-1]["t"] + 0.5
    pulsos += [{"t": t + i * 0.5, "fuerte": i % 3 == 0} for i in range(12)]
    cifras = estimar_cifras(pulsos)
    assert [c["pulsos_por_compas"] for c in cifras] == [4, 3]


def test_anclas_corrigen_fase():
    verdad = compas(8, 4)
    # el modelo acierta los pulsos pero pone el fuerte un pulso tarde
    mal = [{"t": p["t"], "fuerte": (i % 4) == 1} for i, p in enumerate(verdad)]
    anclas = [p["t"] + 0.02 for p in verdad if p["fuerte"]][::3]
    corr = corregir_con_anclas(mal, anclas)
    assert [p["fuerte"] for p in corr] == [p["fuerte"] for p in verdad]


def test_ancla_sin_pulso_se_inserta():
    pulsos = compas(4, 4)
    del pulsos[8]  # el modelo se salta un tiempo fuerte
    corr = corregir_con_anclas(pulsos, [4.5])
    assert any(abs(p["t"] - 4.5) < 1e-6 and p["fuerte"] for p in corr)


def test_ajustar_tiempo_mueve_hacia_anclas():
    pulsos = compas(4, 4)
    corr = corregir_con_anclas(pulsos, [0.53, 6.53], ajustar_tiempo=True)
    assert abs(corr[0]["t"] - 0.53) < 1e-6
    assert abs(corr[4]["t"] - 2.53) < 1e-6
