"""
Mide la lista de pulsos contra una verdad (sintética o anotación humana).

    python -m lab_pulsos.evaluar DIRECTORIO [--checkpoint final0 | --sin-pesos] [--anclas 3]

En DIRECTORIO cada X.wav necesita un X.json con {"pulsos": [{"t", "fuerte"}, ...]}.
Con --sin-pesos el modelo tiene pesos aleatorios: sirve para medir tiempo de CPU y
probar el circuito, NO para medir acierto.
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import soundfile as sf

from lab_pulsos.pulsos import a_lista, corregir_con_anclas, estimar_cifras

TOLS = (0.05, 0.10, 0.20)


def emparejar(ref, est, tol):
    """Emparejamiento uno a uno, voraz por cercanía. Devuelve pares (i_ref, i_est)."""
    ref, est = np.asarray(ref), np.asarray(est)
    if len(ref) == 0 or len(est) == 0:
        return []
    d = np.abs(ref[:, None] - est[None, :])
    cand = sorted(zip(*np.nonzero(d <= tol)), key=lambda ij: d[ij])
    usados_r, usados_e, pares = set(), set(), []
    for i, j in cand:
        if i not in usados_r and j not in usados_e:
            usados_r.add(i)
            usados_e.add(j)
            pares.append((int(i), int(j)))
    return pares


def f_medida(ref, est, tol):
    pares = emparejar(ref, est, tol)
    if len(ref) == 0 and len(est) == 0:
        return 1.0, []
    p = len(pares) / max(len(est), 1)
    r = len(pares) / max(len(ref), 1)
    f = 0.0 if p + r == 0 else 2 * p * r / (p + r)
    errores = [abs(ref[i] - est[j]) for i, j in pares]
    return f, errores


def puntuar(verdad, pulsos):
    ref_b = [p["t"] for p in verdad]
    ref_d = [p["t"] for p in verdad if p["fuerte"]]
    est_b = [p["t"] for p in pulsos]
    est_d = [p["t"] for p in pulsos if p["fuerte"]]
    r = {}
    for tol in TOLS:
        ms = int(tol * 1000)
        r[f"F_pulsos_{ms}"], err = f_medida(ref_b, est_b, tol)
        r[f"F_fuertes_{ms}"], _ = f_medida(ref_d, est_d, tol)
        if ms == 100:
            r["err_mediano_ms"] = 1000 * float(np.median(err)) if err else None
    return r


def media(dicts):
    return {k: (None if any(d[k] is None for d in dicts) else float(np.mean([d[k] for d in dicts])))
            for k in dicts[0]}


def anclas_simuladas(verdad, n, ruido_ms, rng):
    """n tiempos fuertes repartidos por la obra, con error humano gaussiano."""
    fuertes = [p["t"] for p in verdad if p["fuerte"]]
    elegidos = np.linspace(0, len(fuertes) - 1, n).round().astype(int)
    return [fuertes[i] + rng.normal(0, ruido_ms / 1000) for i in elegidos]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("directorio")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--checkpoint", default="final0")
    g.add_argument("--sin-pesos", action="store_true")
    ap.add_argument("--anclas", type=int, default=3)
    ap.add_argument("--ruido-anclas-ms", type=float, default=20.0)
    ap.add_argument("--sorteos", type=int, default=20, help="sorteos del error de las anclas")
    ap.add_argument("--salida", help="JSON con los resultados")
    args = ap.parse_args(argv)

    import torch
    from beat_this.inference import File2Beats

    ckpt = None if args.sin_pesos else args.checkpoint
    t0 = time.perf_counter()
    f2b = File2Beats(checkpoint_path=ckpt, device="cpu")
    carga = time.perf_counter() - t0
    rng = np.random.default_rng(0)
    filas = []
    for wav in sorted(Path(args.directorio).glob("*.wav")):
        verdad = json.loads(wav.with_suffix(".json").read_text())["pulsos"]
        dur = sf.info(str(wav)).duration
        t0 = time.perf_counter()
        beats, downbeats = f2b(str(wav))
        seg = time.perf_counter() - t0
        pulsos = a_lista(beats, downbeats)
        # el efecto de las anclas se promedia sobre varios sorteos del error humano
        sorteos = [anclas_simuladas(verdad, args.anclas, args.ruido_anclas_ms, rng) for _ in range(args.sorteos)]
        con_anclas = media([puntuar(verdad, corregir_con_anclas(pulsos, a)) for a in sorteos])
        con_tiempo = media([puntuar(verdad, corregir_con_anclas(pulsos, a, ajustar_tiempo=True)) for a in sorteos])
        fila = {
            "caso": wav.stem,
            "duracion_s": round(dur, 2),
            "s_por_min_audio": round(60 * seg / dur, 3),
            "cifras_verdad": [c["pulsos_por_compas"] for c in estimar_cifras(verdad)],
            "cifras_est": [c["pulsos_por_compas"] for c in estimar_cifras(pulsos)],
            "modelo": puntuar(verdad, pulsos),
            "con_anclas": con_anclas,
            "con_anclas_y_tiempo": con_tiempo,
        }
        filas.append(fila)
        m, a = fila["modelo"], fila["con_anclas"]
        print(f"{wav.stem:28s} {fila['s_por_min_audio']:6.2f} s/min  "
              f"F100 pulsos {m['F_pulsos_100']:.2f}  fuertes {m['F_fuertes_100']:.2f} -> {a['F_fuertes_100']:.2f}  "
              f"cifras {fila['cifras_est']} (verdad {fila['cifras_verdad']})")
    res = {
        "checkpoint": "ALEATORIO (sin pesos)" if args.sin_pesos else args.checkpoint,
        "hilos_torch": torch.get_num_threads(),
        "carga_modelo_s": round(carga, 2),
        "casos": filas,
    }
    if args.salida:
        Path(args.salida).write_text(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
