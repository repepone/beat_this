"""
Audio sintético con verdad exacta para probar la lista de pulsos.

Cada caso es una lista de compases (pulsos por compás) y una curva de tempo. Se sintetiza
un piano sencillo (armónicos con caída), bajo en el tiempo fuerte, acorde en los demás y
un poco de ruido. Todo se genera aquí: no hay audio de terceros ni licencias que anotar.

    python -m lab_pulsos.sintetico DIRECTORIO
"""

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 22050


def nota(f0, dur, sr=SR, armonicos=6, caida=3.0, amp=1.0):
    t = np.arange(int(dur * sr)) / sr
    x = sum((0.6 ** k) * np.sin(2 * np.pi * f0 * (k + 1) * t) for k in range(armonicos))
    ataque = np.minimum(1.0, t / 0.004)
    return amp * ataque * np.exp(-caida * t) * x


def tiempos(compases, bpm, pausas=None, silencios=(), anacrusa=0):
    """
    Devuelve (lista de pulsos verdad, lista de onsets que suenan).
    bpm: número o función bpm(i_pulso). pausas: {i_pulso: segundos extra antes del pulso}.
    silencios: índices de compás que no suenan (pero siguen contando).
    anacrusa: pulsos de antecompás (los últimos del compás 0, que es incompleto).
    """
    pausas = pausas or {}
    bpm_f = bpm if callable(bpm) else (lambda i: bpm)
    t = 0.5
    verdad, suenan = [], []
    i = 0
    for c, n in enumerate(compases):
        rango = range(n - anacrusa, n) if (c == 0 and anacrusa) else range(n)
        for k in rango:
            t += pausas.get(i, 0.0)
            verdad.append({"t": round(t, 4), "fuerte": k == 0, "compas": c, "pulso": k})
            if c not in silencios:
                suenan.append((t, k == 0, k))
            t += 60.0 / bpm_f(i)
            i += 1
    return verdad, suenan, t + 1.5


def render(suenan, dur, semilla=0):
    rng = np.random.default_rng(semilla)
    y = np.zeros(int(dur * SR) + SR)
    acordes = [(261.6, 329.6, 392.0), (220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (196.0, 246.9, 293.7)]
    for j, (t, fuerte, k) in enumerate(suenan):
        i0 = int(t * SR)
        ac = acordes[(j // 4) % 4]
        if fuerte:
            s = nota(ac[0] / 2, 1.2, caida=2.0, amp=0.9) + 0.5 * sum(nota(f, 1.2, amp=0.4) for f in ac)
        else:
            s = 0.35 * sum(nota(f, 0.6, caida=4.0, amp=0.4) for f in ac[1:])
        y[i0:i0 + len(s)] += s[: len(y) - i0]
    y += 0.003 * rng.standard_normal(len(y))
    return (0.9 * y / np.max(np.abs(y))).astype(np.float32)


def casos():
    def rubato(i):
        return 80 + 30 * np.sin(2 * np.pi * i / 13.0)

    def ritardando(i):
        return max(45.0, 120 - 1.8 * i)

    return {
        "01_tempo_fijo_4x4_100": dict(compases=[4] * 12, bpm=100),
        "02_vals_3x4_150": dict(compases=[3] * 16, bpm=150),
        "03_rubato_fuerte_4x4": dict(compases=[4] * 10, bpm=rubato),
        "04_ritardando_3x4": dict(compases=[3] * 12, bpm=ritardando),
        "05_anacrusa_1_3x4": dict(compases=[3] * 12, bpm=96, anacrusa=1),
        "06_pausa_larga_3s": dict(compases=[4] * 10, bpm=90, pausas={20: 3.0}),
        "07_compas_silencio_4x4": dict(compases=[4] * 10, bpm=100, silencios=(5,)),
        "08_cambio_4_3_5": dict(compases=[4] * 4 + [3] * 4 + [5] * 4 + [4] * 2, bpm=110),
    }


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    out = Path(argv[0] if argv else "lab_pulsos/audio_sintetico")
    out.mkdir(parents=True, exist_ok=True)
    for nombre, cfg in casos().items():
        verdad, suenan, dur = tiempos(
            cfg["compases"], cfg["bpm"], cfg.get("pausas"), cfg.get("silencios", ()), cfg.get("anacrusa", 0)
        )
        sf.write(out / f"{nombre}.wav", render(suenan, dur), SR)
        (out / f"{nombre}.json").write_text(json.dumps({"pulsos": verdad, "duracion": dur}, indent=1))
        print(nombre, f"{dur:.1f}s", len(verdad), "pulsos")


if __name__ == "__main__":
    main()
