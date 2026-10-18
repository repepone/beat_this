"""
Audio -> lista de pulsos [{t, fuerte}] con beat_this, solo CPU.

Uso:
    python -m lab_pulsos.pulsos grabacion.wav -o pulsos.json
    python -m lab_pulsos.pulsos grabacion.wav --anclas 1.02,5.11,9.20 -o pulsos.json
    python -m lab_pulsos.pulsos grabacion.wav --solo-lista   # solo [{t, fuerte}]

Salida por defecto:
    {"pulsos": [{"t": 0.52, "fuerte": true}, ...],
     "cifras": [{"desde": 0.52, "pulsos_por_compas": 4}, ...]}

"cifras" solo da el numerador (pulsos por compas); el audio no dice si es 3/4 o 3/8.
"""

import argparse
import json
import sys

import numpy as np


def detectar(audio_path, checkpoint="final0", dbn=False):
    """Devuelve (beats, downbeats) en segundos usando beat_this en CPU."""
    from beat_this.inference import File2Beats

    f2b = File2Beats(checkpoint_path=checkpoint, device="cpu", dbn=dbn)
    beats, downbeats = f2b(audio_path)
    return np.asarray(beats, dtype=float), np.asarray(downbeats, dtype=float)


def a_lista(beats, downbeats, tol=0.03):
    """Une beats y downbeats en [{t, fuerte}]. Un downbeat sin beat cercano se añade."""
    beats = np.sort(np.asarray(beats, dtype=float))
    downbeats = np.sort(np.asarray(downbeats, dtype=float))
    fuerte = np.zeros(len(beats), dtype=bool)
    extra = []
    for d in downbeats:
        if len(beats):
            i = int(np.argmin(np.abs(beats - d)))
            if abs(beats[i] - d) <= tol:
                fuerte[i] = True
                continue
        extra.append(d)
    ts = np.concatenate([beats, extra])
    fs = np.concatenate([fuerte, np.ones(len(extra), dtype=bool)])
    orden = np.argsort(ts, kind="stable")
    return [{"t": round(float(ts[i]), 4), "fuerte": bool(fs[i])} for i in orden]


def estimar_cifras(pulsos, min_compases=2):
    """
    Pulsos por compas por tramos. Cuenta los pulsos entre tiempos fuertes seguidos y
    agrupa compases iguales. Un tramo de menos de `min_compases` compases se funde con
    el anterior (suele ser un error suelto, o una anacrusa al principio).
    """
    idx = [i for i, p in enumerate(pulsos) if p["fuerte"]]
    if len(idx) < 2:
        return []
    compases = [(pulsos[a]["t"], b - a) for a, b in zip(idx[:-1], idx[1:])]
    tramos = []
    for t, n in compases:
        if tramos and tramos[-1]["pulsos_por_compas"] == n:
            tramos[-1]["compases"] += 1
        else:
            tramos.append({"desde": t, "pulsos_por_compas": n, "compases": 1})
    # fundir tramos cortos con el vecino anterior (o el siguiente si es el primero)
    limpios = []
    for tr in tramos:
        if tr["compases"] < min_compases and limpios:
            limpios[-1]["compases"] += tr["compases"]
        else:
            limpios.append(dict(tr))
    if len(limpios) > 1 and limpios[0]["compases"] < min_compases:
        limpios[1]["desde"] = limpios[0]["desde"]
        limpios[1]["compases"] += limpios[0]["compases"]
        limpios.pop(0)
    # tras fundir pueden quedar dos tramos seguidos iguales
    final = []
    for tr in limpios:
        if final and final[-1]["pulsos_por_compas"] == tr["pulsos_por_compas"]:
            final[-1]["compases"] += tr["compases"]
        else:
            final.append(tr)
    return final


def corregir_con_anclas(pulsos, anclas, max_dist=None, ajustar_tiempo=False):
    """
    Corrección mínima con tiempos fuertes marcados a mano (`anclas`, en segundos).

    1. Cada ancla se pega al pulso detectado más cercano. Si no hay ninguno a menos de
       `max_dist` (por defecto, media distancia típica entre pulsos), se inserta un pulso.
    2. Fase: si más de la mitad de las anclas dicen que el fuerte del modelo está corrido
       el mismo número de pulsos, se corre en toda la obra. Si no, el arreglo es local: el
       ancla pasa a fuerte y se quita el fuerte del modelo a 1-2 pulsos de ella.
    3. Si `ajustar_tiempo`, se corrige además el desfase entre el ancla y el pulso,
       interpolando linealmente entre anclas (constante fuera de ellas).
    """
    pulsos = [dict(p) for p in pulsos]
    anclas = sorted(float(a) for a in anclas)
    if not anclas:
        return pulsos
    if not pulsos:
        return [{"t": round(a, 4), "fuerte": True} for a in anclas]
    ts = np.array([p["t"] for p in pulsos])
    periodo = float(np.median(np.diff(ts))) if len(ts) > 1 else 0.5
    if max_dist is None:
        max_dist = periodo / 2

    # 1. pegar o insertar
    for a in anclas:
        ts = np.array([p["t"] for p in pulsos])
        i = int(np.argmin(np.abs(ts - a)))
        if abs(ts[i] - a) > max_dist:
            pulsos.append({"t": round(a, 4), "fuerte": True})
            pulsos.sort(key=lambda p: p["t"])
    ts = np.array([p["t"] for p in pulsos])
    idx_ancla = [int(np.argmin(np.abs(ts - a))) for a in anclas]
    fuerte = np.array([p["fuerte"] for p in pulsos], dtype=bool)
    nuevo = fuerte.copy()

    # 2. fase: desplazamiento global si la mayoría de anclas coincide; si no, arreglo local
    def desfase(ia, marcas):
        fuertes = np.flatnonzero(marcas)
        if len(fuertes) == 0:
            return None
        return int(ia - fuertes[np.argmin(np.abs(fuertes - ia))])

    desps = [desfase(ia, fuerte) for ia in idx_ancla]
    validos = [d for d in desps if d]
    if validos:
        comun = max(set(validos), key=validos.count)
        if validos.count(comun) > len(idx_ancla) / 2:
            src = np.flatnonzero(fuerte) + comun
            nuevo[:] = False
            nuevo[src[(src >= 0) & (src < len(pulsos))]] = True
    for ia in idx_ancla:
        d = desfase(ia, nuevo)
        if d and abs(d) <= 2:
            nuevo[ia - d] = False  # el fuerte del modelo estaba corrido en este compás
        nuevo[ia] = True

    # 3. ajuste de tiempo opcional
    if ajustar_tiempo:
        xs = ts[idx_ancla]
        ds = np.array(anclas) - xs
        ts = ts + np.interp(ts, xs, ds)

    return [{"t": round(float(t), 4), "fuerte": bool(f)} for t, f in zip(ts, nuevo)]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Audio -> pulsos [{t, fuerte}] con beat_this (CPU)")
    ap.add_argument("audio")
    ap.add_argument("-o", "--salida", help="fichero JSON (por defecto, a la salida estándar)")
    ap.add_argument("--checkpoint", default="final0",
                    help="nombre del checkpoint de beat_this o ruta local a un .ckpt")
    ap.add_argument("--anclas", help="tiempos fuertes marcados a mano, en segundos, separados por comas")
    ap.add_argument("--ajustar-tiempo", action="store_true",
                    help="además de la fase, mover los pulsos para que coincidan con las anclas")
    ap.add_argument("--solo-lista", action="store_true", help="escribir solo [{t, fuerte}]")
    args = ap.parse_args(argv)

    beats, downbeats = detectar(args.audio, args.checkpoint)
    pulsos = a_lista(beats, downbeats)
    if args.anclas:
        anclas = [float(x) for x in args.anclas.split(",") if x.strip()]
        pulsos = corregir_con_anclas(pulsos, anclas, ajustar_tiempo=args.ajustar_tiempo)
    out = pulsos if args.solo_lista else {"pulsos": pulsos, "cifras": estimar_cifras(pulsos)}
    texto = json.dumps(out, ensure_ascii=False, indent=1)
    if args.salida:
        with open(args.salida, "w") as f:
            f.write(texto + "\n")
    else:
        sys.stdout.write(texto + "\n")


if __name__ == "__main__":
    main()
