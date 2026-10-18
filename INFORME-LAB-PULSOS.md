# Informe · lab-pulsos · lista de pulsos desde una grabación con beat_this

Rama `lab-pulsos` del fork `repepone/beat_this`. Fecha: 18-oct-2026.

## Resumen en cuatro líneas

1. **Licencia: bien.** El código y los pesos publicados de beat_this son MIT (leído).
2. **Bloqueo: los pesos no se han podido descargar.** La red de esta sesión en la nube solo deja pasar
   PyPI, npm y GitHub. El servidor de los pesos (`cloud.cp.jku.at`) da 403, igual que HuggingFace, Zenodo,
   Wikimedia y archive.org. **Por eso no hay ninguna medida de acierto de beat_this en este informe.**
3. **Sí está hecho:** el CLI (audio → `[{t, fuerte}]` + cifra por tramos), la corrección con anclas, 8 audios
   sintéticos con verdad exacta, el evaluador a 50/100/200 ms y la medida de tiempo de CPU (que no depende del
   valor de los pesos, solo de la arquitectura).
4. **Para terminar la medida:** abrir `cloud.cp.jku.at` en la red del entorno (o copiar `final0.ckpt` en local)
   y lanzar un solo comando (ver «Cómo completar la medida»). Coste estimado: minutos de CPU, nada de dinero.

## 1. Licencias

| Cosa | Licencia | Fuente | Tipo |
|---|---|---|---|
| Código beat_this | MIT | `LICENSE` (© 2024 JKU Linz) y `pyproject.toml` | leído |
| Pesos publicados (`final0`, etc.) | MIT | `README.md`, sección *License*, commit b95c8ab: «The code and the published model weights are released under the MIT license» | leído |
| Datos de entrenamiento | algunos con copyright o CC limitadas | misma sección del README; el README dice que cada usuario debe valorar si le afecta | leído |
| `roformer.py` (parte del modelo) | MIT (deriva de BS-RoFormer, lucidrains) | cabecera del fichero | leído |
| Audio de prueba | generado aquí con `lab_pulsos/sintetico.py`; sin terceros | — | — |

Descarté `maddad`, un paquete de PyPI que también usa beat_this: es CC BY-NC 4.0 y su rueda pesa 6 MB, así que
no trae los pesos (unos 78 MB).

## 2. El CLI

```
python -m lab_pulsos.pulsos grabacion.wav -o pulsos.json
python -m lab_pulsos.pulsos grabacion.wav --anclas 1.02,5.11,9.20 -o pulsos.json
python -m lab_pulsos.pulsos grabacion.wav --solo-lista          # solo [{t, fuerte}]
python -m lab_pulsos.pulsos grabacion.wav --checkpoint /ruta/final0.ckpt
```

Salida:

```json
{"pulsos": [{"t": 0.52, "fuerte": true}, {"t": 1.12, "fuerte": false}, ...],
 "cifras": [{"desde": 0.52, "pulsos_por_compas": 4, "compases": 4},
            {"desde": 9.24, "pulsos_por_compas": 3, "compases": 4}]}
```

- Solo CPU (`device="cpu"`), con el postproceso «minimal» de beat_this (no necesita madmom).
- **Cifra:** solo da el numerador, es decir, cuántos pulsos hay entre dos tiempos fuertes. El audio no distingue
  3/4 de 3/8. Un compás suelto distinto se funde con el tramo vecino (se toma por error del modelo); por tanto,
  **un cambio de compás que dure un solo compás no se reporta**. El último compás de la obra no se cuenta, porque
  no hay un tiempo fuerte detrás.
- Código: `lab_pulsos/pulsos.py`. Pruebas de lógica: `tests/test_lab_pulsos.py` (5 pasan).

## 3. Medida en grabaciones

### 3a. Audios de prueba (8, sintéticos)

No pude bajar ninguna grabación libre porque las fuentes habituales están bloqueadas (ver arriba). Generé 8 casos
de 21-34 s: un piano sencillo, bajo en el tiempo fuerte, acordes y un poco de ruido. La verdad es exacta, porque
la pongo yo.

| Caso | Qué prueba |
|---|---|
| 01_tempo_fijo_4x4_100 | tempo fijo, 100 BPM |
| 02_vals_3x4_150 | 3/4 rápido |
| 03_rubato_fuerte_4x4 | tempo que oscila entre 50 y 110 BPM |
| 04_ritardando_3x4 | de 120 a 57 BPM seguidos |
| 05_anacrusa_1_3x4 | un pulso de antecompás |
| 06_pausa_larga_3s | calderón de 3 s a mitad de obra |
| 07_compas_silencio_4x4 | un compás entero en silencio, que sigue contando |
| 08_cambio_4_3_5 | 4/4 → 3/4 → 5/4 → 4/4 |

Ojo: un audio sintético es más fácil que una grabación real (ataques limpios, sin reverberación ni gente). Aunque
se midiera bien, serviría para hallar fallos de lógica (anacrusa, silencio, pausa), no para prometer acierto.

### 3b. Acierto: **no medido**

- Con los pesos reales: no se pudo, por el bloqueo.
- Sí ejecuté todo el circuito con **pesos aleatorios**, solo para comprobar que funciona de punta a punta. Sale
  F ≈ 0,3, que es ruido, como era de esperar. **Ese número no dice nada de beat_this** y no lo uso.
- **Anotaciones humanas públicas:** existen (por ejemplo, GTZAN o Ballroom tienen beats anotados por personas),
  pero su audio no tiene licencia libre clara o estaba en hosts bloqueados. **En esta sesión no comparé con
  ninguna anotación humana.** El evaluador acepta cualquier anotación: `X.wav` + `X.json`.
- **Lo que dicen los autores (de memoria, sin verificar en esta sesión):** el artículo de beat_this (ISMIR 2024)
  da una F-medida de beats alta, de alrededor de 0,9, en pop, rock y ballroom, y bastante menos en clásica y en
  piano con rubato. Hay que confirmarlo en el artículo y, sobre todo, medirlo en nuestro tipo de música.
- **Aviso del README (leído):** el modelo `final0` se entrenó con todo menos GTZAN. Evaluarlo con piezas de sus
  datos de entrenamiento da resultados injustamente buenos.

### 3c. Tiempo de CPU: **medido**

Intel Xeon a 2,8 GHz, 4 núcleos, torch 2.14.1. Pieza de 3 minutos; mínimo y máximo de 3 repeticiones:

| Hilos | Segundos de proceso por minuto de audio |
|---|---|
| 4 | 1,97 – 2,10 |
| 2 | 3,31 – 3,45 |
| 1 | 5,76 – 5,89 |

- En piezas cortas, de 21 a 34 s, el coste por minuto varía entre 1,6 y 3,6 s/min. El modelo trocea en bloques
  de 30 s, así que una pieza de 31 s cuesta casi lo mismo que una de 60.
- Memoria máxima (RSS) con una pieza de 3 min: unos 745 MB.
- Carga del modelo: menos de 1 s (medido con pesos aleatorios; leer un `.ckpt` de 81 MB desde disco añade poco).
- El tiempo no depende del valor de los pesos, porque la arquitectura y los parámetros son los mismos que en
  `final0` (20,25 M parámetros). Por eso esta medida sí vale.

## 4. Corrección con anclas

Qué hace `corregir_con_anclas` cuando quien graba marca 3 o 4 tiempos fuertes a mano:

1. Pega cada ancla al pulso detectado más cercano. Si no hay ninguno a menos de medio pulso, inserta un pulso.
2. **Fase:** alrededor de cada ancla, desplaza la marca de «fuerte» los pulsos que haga falta para que el ancla
   caiga en fuerte. Respeta los cambios de compás que haya visto el modelo. Con esto se arregla el error típico
   de «el 1 está en el 2».
3. Opcional (`--ajustar-tiempo`): mueve los pulsos hacia las anclas, interpolando el desfase entre ellas.

**Mejora: no medida** con el modelo real. Las pruebas comprueban que la lógica hace lo que dice: recupera la fase
desplazada un pulso e inserta un fuerte que falta. El evaluador ya simula anclas humanas con un error gaussiano de
20 ms, como vuestra medida de 18-22 ms, y da tres columnas: modelo solo, con anclas (fase) y con anclas + tiempo.

Lo que espero, sin medirlo: las anclas deberían ayudar sobre todo en la **fase del tiempo fuerte**, que es donde
más fallan los detectores. En la **precisión de cada pulso** ayudarán poco o nada. Si el modelo ya acierta los
pulsos con unos 10-20 ms de error, tirar de anclas con 20 ms de error humano puede empeorarlo. Por eso
`--ajustar-tiempo` va apagado por defecto. El dato que decide es la columna «con anclas y tiempo» frente a
«modelo» en `err_mediano_ms`.

Lo que las anclas **no** arreglan: un tempo detectado al doble o a la mitad, o un tramo de rubato donde el modelo
pierde pulsos entre dos anclas. Para eso haría falta otra cosa (por ejemplo, rehacer los pulsos entre anclas
contando los que debe haber).

## 5. Qué haría falta para usarlo en local

- **Pesos:** `final0.ckpt`, unos 78 MB según el README (20,25 M parámetros en fp32, medido, que dan unos 81 MB decimales). El README ofrece `small0`, de unos
  8,1 MB (leído); su acierto y su velocidad no los he medido.
- **Dependencias Python:** `torch`, `torchaudio`, `numpy`, `einops`, `rotary-embedding-torch` y `soxr`, más
  `soundfile` para leer audio.
- **Tamaño de torch:** el torch de PyPI para Linux trae CUDA, unos 1,2 GB, más 3,2 GB de librerías `nvidia`.
  Para usarlo en local conviene instalar el torch «solo CPU», que es varias veces más pequeño (supuesto: unos
  pocos cientos de MB; en macOS el de PyPI ya es solo CPU). No pude instalarlo aquí porque `download.pytorch.org` también está bloqueado.
- **Alternativa más ligera (vista en una búsqueda, no probada):** hay una conversión de beat_this a GGUF publicada
  por un tercero en HuggingFace (`cstr/beat-this-GGUF`). Habría que comprobar su licencia y que dan lo mismo que el original antes de usarlas.
- **RAM:** unos 750 MB para una pieza de 3 min.

## 6. Cómo completar la medida (cuando haya pesos)

```
pip install -e . einops rotary-embedding-torch soxr soundfile
python -m lab_pulsos.sintetico audio_prueba/
python -m lab_pulsos.evaluar audio_prueba/ --checkpoint final0 --anclas 3 --salida resultados.json
python -m lab_pulsos.evaluar audio_prueba/ --checkpoint final0 --anclas 4
```

Para grabaciones reales, deja junto a cada `X.wav` un `X.json` con `{"pulsos": [{"t":…, "fuerte":…}]}` anotado
a mano (sirve la misma herramienta de marcar golpes de la claqueta).

## 7. Qué está medido, leído o supuesto

| Afirmación | Tipo |
|---|---|
| Código y pesos MIT | leído (LICENSE, README) |
| Pesos y audio libre inaccesibles desde esta sesión | medido (403 del proxy) |
| 2,0 s de CPU por minuto de audio con 4 hilos; 5,8 s con 1 | medido |
| 20,25 M parámetros, unos 81 MB, unos 745 MB de RAM | medido |
| CLI, cifras y anclas hacen lo que dicen | medido con pruebas de lógica, no con el modelo |
| Acierto de beat_this en rubato, anacrusa, pausa y compás en silencio | **no medido** |
| Mejora con 3 o 4 anclas | **no medido** |
| F ≈ 0,9 en pop/rock y peor en clásica | de memoria, sin verificar ni medir |
| `small0` de unos 8,1 MB | leído (README) |
| Las anclas ayudan sobre todo en la fase del fuerte | supuesto |

## 8. Presupuesto

No he usado ningún servicio de pago ni cuentas externas. El gasto es solo el de esta sesión de cómputo, muy por
debajo de los 25 US$. Terminar la medida (paso 6) son unos minutos de CPU.
