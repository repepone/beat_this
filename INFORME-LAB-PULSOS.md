# Informe · lab-pulsos · lista de pulsos desde una grabación con beat_this

Rama `lab-pulsos` del fork `repepone/beat_this`. Fecha: 18-oct-2026. Segunda versión: ya con los pesos reales.

## Resumen

1. **Licencia: bien.** El código y los pesos publicados son MIT (leído).
2. **Funciona bien (medido)** con tempo fijo, 3/4, anacrusa, un compás en silencio y una pausa larga: acierta
   del 95 al 100 % de los pulsos y del 87 al 100 % de los tiempos fuertes, a ±50 ms.
3. **Falla (medido)** en tres casos:
   - **rubato fuerte:** acierta el 68 % de los pulsos;
   - **ritardando (de 120 a 57 BPM):** deja sin marcar la mitad de los pulsos y acierta el 60 %;
   - **cambios de compás:** acierta el 82 % de los pulsos y la cifra estimada sale mal.
4. **Precisión de cada pulso acertado:** error mediano de 5 ms y 20 ms en el 90 % de los casos. Es comparable a
   vuestra marca manual (18-22 ms). El modelo trabaja en una rejilla de 20 ms, así que no baja de ±10 ms.
5. **Anclas (3 o 4 fuertes a mano):** mejoran poco, porque el modelo casi nunca se equivoca de fase.
   - final0: los tiempos fuertes mejoran solo en el cambio de compás (0,76 → 0,83 con 3 anclas).
   - small0: mejoran en rubato, ritardando y vals (de +0,05 a +0,08).
   - Mover los pulsos hacia las anclas **empeora** la precisión (de 0-17 ms a 11-24 ms), así que va apagado.
   - **Las anclas no arreglan el problema real, que es perder o duplicar pulsos.**
6. **Coste en CPU:** final0, con 4 hilos, gasta 2,2-2,4 s por minuto de audio. El modelo pesa 81 MB.
7. **Límite importante:** todo está medido con **audio sintético** (8 piezas de piano generadas aquí). No pude
   bajar grabaciones reales con licencia libre (Wikimedia y archive.org siguen bloqueados) y **no hay comparación
   con anotaciones humanas**.

## 1. Licencias

| Cosa | Licencia | Fuente | Tipo |
|---|---|---|---|
| Código beat_this | MIT | `LICENSE` (© 2024 JKU Linz), `pyproject.toml` | leído |
| Pesos `final0` y `small0` | MIT | README, sección *License* (commit b95c8ab): «The code and the published model weights are released under the MIT license» | leído |
| Datos de entrenamiento | algunos con copyright o CC limitadas | misma sección; el README dice que cada usuario debe valorar si le afecta | leído |
| `roformer.py` | MIT (deriva de BS-RoFormer) | cabecera del fichero | leído |
| Audio de prueba | generado aquí (`lab_pulsos/sintetico.py`), sin terceros | — | — |

Pesos descargados de `cloud.cp.jku.at` (la URL oficial del código):

- `final0.ckpt`: 81 058 141 bytes, sha256 `8c328b45…eb8331`.
- `small0.ckpt`: 8 451 101 bytes, sha256 `6074be2c…7d47b`.

## 2. El CLI

```
python -m lab_pulsos.pulsos grabacion.wav -o pulsos.json
python -m lab_pulsos.pulsos grabacion.wav --anclas 1.02,5.11,9.20 -o pulsos.json
python -m lab_pulsos.pulsos grabacion.wav --solo-lista          # solo [{t, fuerte}]
python -m lab_pulsos.pulsos grabacion.wav --checkpoint small0   # modelo pequeño
```

Salida:

```json
{"pulsos": [{"t": 0.5, "fuerte": true}, {"t": 1.1, "fuerte": false}, ...],
 "cifras": [{"desde": 0.5, "pulsos_por_compas": 4, "compases": 4},
            {"desde": 9.2, "pulsos_por_compas": 3, "compases": 4}]}
```

- Solo CPU, con el postproceso «minimal» de beat_this (no necesita madmom).
- La **cifra** solo da el numerador, porque el audio no distingue 3/4 de 3/8.
- Un compás suelto distinto se funde con el tramo vecino, así que un cambio que dure un solo compás no se reporta.
  El último compás no se cuenta.
- La cifra **solo es fiable si los pulsos lo son**. Si el modelo marca un pulso de cada dos, un 4/4 sale como «2».

## 3. Medida

### 3a. Material

Son 8 piezas sintéticas de 21 a 34 s: piano sencillo, bajo en el tiempo fuerte y un acorde por compás. La verdad
es exacta porque la pongo yo.

Corregí un fallo de mi generador tras la primera pasada: cambiaba de acorde cada 4 notas aunque el compás fuera
de 3, y eso contradecía la métrica. Las cifras de abajo son las del generador corregido.

**Advertencias sobre el material:**

- Es más fácil que una grabación real: ataques limpios, sin sala ni rubato «humano».
- Los tempos de 100 y 150 BPM caen justo en la rejilla de 20 ms del modelo. Por eso salen errores de 0,0 ms, que
  son un artefacto. Los casos que no caen en la rejilla dan una idea más honesta, de 9 a 17 ms.

### 3b. Resultados con final0 (el modelo principal)

F-medida: 1 es perfecto. Combina pulsos de menos y de más, con la tolerancia indicada.

| Caso | F pulsos 50 / 100 / 200 ms | F fuertes 50 / 100 / 200 ms | Error mediano (ms) | Cifra estimada (verdad) |
|---|---|---|---|---|
| Tempo fijo 4/4, 100 BPM | 1,00 / 1,00 / 1,00 | 0,96 / 0,96 / 0,96 | 0* | 4 (4) ✔ |
| Vals 3/4, 150 BPM | 0,98 / 0,98 / 0,98 | 0,97 / 0,97 / 0,97 | 10 | 3 (3) ✔ |
| Rubato fuerte 4/4 (50↔110 BPM) | 0,68 / 0,68 / 0,68 | 0,71 / 0,71 / 0,71 | 9 | 2, 3, 1 (4) ✘ |
| Ritardando 3/4 (120→57 BPM) | 0,60 / 0,60 / 0,67 | 0,87 / 0,87 / 0,87 | 17 | 2 (3) ✘ |
| Anacrusa de 1 pulso, 3/4 | 0,97 / 0,97 / 0,97 | 1,00 / 1,00 / 1,00 | 10 | 3 (3) ✔ |
| Pausa larga (calderón de 3 s) | 0,95 / 0,95 / 0,95 | 0,87 / 0,87 / 0,87 | 13 | 4 (4) ✔ |
| Un compás en silencio, 4/4 | 1,00 / 1,00 / 1,00 | 0,95 / 0,95 / 0,95 | 0* | 4 (4) ✔ |
| Cambio 4/4 → 3/4 → 5/4 → 4/4 | 0,82 / 0,82 / 0,82 | 0,76 / 0,76 / 0,76 | 6 | 2, 3, 1, 4 (4, 3, 5) ✘ |
| **Media de los 8** | **0,88** | **0,89** | | **5 de 8** |

\* Artefacto de la rejilla de 20 ms (ver 3a).

La tolerancia apenas cambia los resultados: cuando el modelo acierta un pulso, acierta a menos de 50 ms. Los
fallos no son de precisión, son pulsos que faltan o que sobran.

**Dónde falla y cómo (mirado caso a caso):**

- **Rubato fuerte:** cuando el tempo se acelera o se frena, pierde pulsos (12 de 40) y mete otros donde no hay.
  Pone tiempos fuertes de más (18 en lugar de 10).
- **Ritardando:** pierde 19 de los 36 pulsos, y **ya desde el principio** (a unos 120 BPM), no solo en la parte
  lenta: deja pulsos intermedios sin marcar. Los tiempos fuertes siguen casi bien (11 de 12, F 0,87).
- **Cambio de compás:** acierta los fuertes del primer tramo en 4/4, pero en el 3/4 se salta casi todos y en el
  5/4 pone fuertes de más. Además pierde 17 de los 56 pulsos, ya en el primer 4/4. La cifra estimada no sirve aquí.
- **Pausa larga:** dentro del calderón de 3 s se inventa 2 pulsos que no existen (y uno lo marca como fuerte),
  y añade otros 2 en la cola final.
- **Anacrusa:** salta el pulso de antecompás, el primer sonido, pero acierta todos los tiempos fuertes.
- **Compás en silencio:** lo rellena bien. Sigue contando los pulsos durante el silencio.
- **Final de la obra:** en casi todos los casos añade un tiempo fuerte de más al final de la cola de sonido. Por
  eso los fuertes salen a 0,95-0,96 y no a 1,00 en los casos fáciles.

### 3c. small0 (el modelo pequeño, 8,5 MB)

Media de los 8 casos: F pulsos 0,82 y F fuertes 0,85, con la cifra bien en 2 de 8. Es claramente peor que final0:
**va a la mitad de tempo en el caso más fácil** (tempo fijo a 100 BPM: F pulsos 0,66, cifra «2»). No lo recomiendo
salvo que el tamaño mande.

### 3d. Anotaciones humanas: **no comparado**

No había grabaciones reales accesibles desde la sesión: Wikimedia y archive.org siguen bloqueados, y los conjuntos
anotados conocidos, como GTZAN o Ballroom, no tienen audio de licencia libre clara. Todo lo anterior es frente a una
verdad sintética, no humana.

### 3e. Tiempo de CPU: **medido**

Intel Xeon a 2,8 GHz, 4 núcleos, torch 2.14.1, pieza de 3 min, 3 repeticiones:

| Modelo | 4 hilos | 1 hilo | Carga del modelo |
|---|---|---|---|
| final0 | 2,15-2,41 s por minuto de audio | 5,57-5,97 s/min | 0,31 s |
| small0 | 1,23-1,29 s/min | 3,20-3,47 s/min | 0,07 s |

- Memoria máxima: unos 860 MB con los dos modelos cargados a la vez (unos 745 MB con uno solo).
- El modelo trocea en bloques de 30 s: una pieza de 31 s cuesta casi lo mismo que una de 60. En las piezas cortas
  de prueba salieron de 1,6 a 4,5 s/min.

## 4. Corrección con anclas

Simulé lo que haría quien graba: 3 o 4 tiempos fuertes repartidos por la obra, cada uno con un error humano
gaussiano de 20 ms, como vuestra medida de 18-22 ms. Promedié 20 sorteos por caso.

**Qué hace la corrección** (`corregir_con_anclas`):

1. Pega cada ancla al pulso detectado más cercano. Si no hay ninguno a menos de medio pulso, inserta uno.
2. **Fase:** si más de la mitad de las anclas dicen que el fuerte del modelo está corrido el mismo número de
   pulsos, lo corre en toda la obra. Si no, arregla solo el compás del ancla.
3. Opcional, con `--ajustar-tiempo`: mueve los pulsos hacia las anclas.

En la primera versión, el paso 2 desplazaba los fuertes de toda una zona. Con un ancla en un compás aislado mal
marcado, eso **empeoraba** el caso del cambio de compás (de 0,76 a 0,62). Lo cambié a la regla de arriba y añadí
una prueba de lógica para ese caso.

**Resultado (medido), F de fuertes a 100 ms:**

| Caso | final0: modelo → 3 anclas / 4 anclas | small0: modelo → 3 anclas / 4 anclas |
|---|---|---|
| Vals 3/4 | 0,97 → 0,97 / 0,97 | 0,81 → 0,81 / **0,86** |
| Rubato fuerte | 0,71 → 0,71 / 0,71 | 0,56 → **0,64** / **0,64** |
| Ritardando | 0,87 → 0,87 / 0,87 | 0,86 → **0,91** / **0,91** |
| Cambio de compás | 0,76 → **0,83** / 0,76 | 0,73 → 0,73 / 0,75 |
| Los otros 4 casos | sin cambio | sin cambio |

- La fase con anclas **nunca empeora** ningún caso tras el arreglo, pero mejora poco: final0 casi nunca se
  equivoca de fase. Lo que falla son pulsos perdidos o duplicados, y eso las anclas de fase no lo tocan.
- Que 4 anclas no ganen a 3 en el caso del cambio de compás tiene una razón: depende de en qué compases caen las
  anclas. Con 3 anclas, una cae en un compás que el modelo tenía mal; con 4, no.
- **Mover los pulsos hacia las anclas empeora** la precisión en todos los casos. El error mediano sube de 0-17 ms
  a 11-24 ms, porque el error humano de 20 ms es mayor que el del modelo. Por eso `--ajustar-tiempo` va apagado.

**Comparado con vuestra medida manual** (3 anclas sin máquina, 18-22 ms de error típico): en los pulsos que
acierta, final0 está en 5 ms de mediana y 20 ms en el 90 % de los casos. Es igual o mejor, pero solo donde no
pierde pulsos.

**Probado y descartado:** afinar cada pulso entre cuadros (interpolación parabólica del pico) no mejora en
conjunto: la mediana pasa de 5,0 a 7,3 ms y el p90 de 20,0 a 18,2 ms. No lo he incluido.

## 5. Qué haría falta para que sirva de verdad

1. **Medir con grabaciones reales** de nuestro tipo de música, con los golpes marcados a mano, en local (nada de
   VisualScore a la nube). El evaluador ya acepta `X.wav` + `X.json`.
2. **Recuperar pulsos perdidos usando las anclas.** Es el fallo principal (ritardando, cambio de compás, small0
   a mitad de tempo). Si quien graba dice cuántos pulsos hay por compás, o marca dos fuertes seguidos, se puede
   comprobar el número de pulsos entre anclas y partir o fundir pulsos. No está hecho.
3. **No fiarse de la cifra automática.** Mejor que la diga quien graba, o que se tome de la partitura.
4. Probar el postproceso DBN de beat_this (necesita `madmom`), que impone un tempo más regular. Podría ayudar con
   el ritardando y estropear el rubato. No está medido.

## 6. Qué haría falta para usarlo en local

- **Pesos:** `final0.ckpt`, 81 MB. Hay `small0`, de 8,5 MB, pero es peor (3c).
- **Dependencias:** `torch`, `torchaudio`, `numpy`, `einops`, `rotary-embedding-torch`, `soxr` y `soundfile`.
- **torch:** el de PyPI para Linux trae CUDA, 1,2 GB más 3,2 GB de librerías nvidia (medido). Conviene instalar el
  torch «solo CPU»; supongo que pesa unos pocos cientos de MB, no lo he medido. En macOS el de PyPI ya es solo CPU.
- **RAM:** unos 750 MB. **CPU:** unos 2-6 s por minuto de audio en un portátil normal (supuesto, a partir de
  la medida en el Xeon).
- **Alternativa ligera:** hay una conversión a GGUF publicada por un tercero (`cstr/beat-this-GGUF`). La vi en una
  búsqueda; no está probada y su licencia no está comprobada.

## 7. Cómo repetir la medida

```
pip install -e . einops rotary-embedding-torch soxr soundfile
python -m lab_pulsos.sintetico audio_prueba/
python -m lab_pulsos.evaluar audio_prueba/ --checkpoint final0 --anclas 3 --salida resultados.json
python -m lab_pulsos.evaluar audio_prueba/ --checkpoint small0 --anclas 4
python -m pytest tests/test_lab_pulsos.py
```

## 8. Qué está medido, leído o supuesto

| Afirmación | Tipo |
|---|---|
| Código y pesos MIT | leído |
| final0: F de pulsos 0,88 y de fuertes 0,89 de media; falla en rubato, ritardando y cambio de compás | medido (audio sintético) |
| Error del pulso acertado: 5 ms de mediana, 20 ms en el 90 % | medido (sintético; la rejilla de 20 ms lo favorece) |
| Las anclas mejoran poco la fase y nunca la empeoran; ajustar el tiempo empeora | medido (anclas simuladas con 20 ms de error) |
| final0: 2,2-2,4 s/min con 4 hilos; small0: 1,2-1,3 s/min | medido |
| Igual de bien con grabaciones reales | **no medido**; supongo que irá peor |
| Comparación con anotaciones humanas | **no medido** |
| Torch solo CPU de unos pocos cientos de MB; 2-6 s/min en un portátil | supuesto |
| DBN, arreglo de tempo con anclas | no hecho |

## 9. Presupuesto

No he usado servicios de pago ni cuentas externas. El gasto es solo el cómputo de esta sesión, muy por debajo de
25 US$.
