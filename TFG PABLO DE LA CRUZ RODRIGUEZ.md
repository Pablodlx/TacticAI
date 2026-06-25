UNIVERSIDAD SAN PABLO - CEU

ESCUELA POLITÉCNICA SUPERIOR

GRADO EN INGENIERÍA DE SISTEMAS DE INFORMACIÓN

TRABAJO FIN DE GRADO

Sistema de análisis táctico en tiempo
real mediante visión por computador e
IA para generar recomendaciones al
cuerpo técnico en fútbol

Real-time tactical analysis system using
computer vision and AI to generate
recommendations for coaching staff in
football

Autor: Pablo de la Cruz Rodríguez
Tutor: Raúl García García
Co-tutor: Raúl A. del Águila Escobar

Junio  2026

 UNIVERSIDAD  SAN  PABLO-CEU

ESCUELA POLITÉCNICA SUPERIOR

 División de Ingeniería

Calificación del Trabajo Fin de Grado

Datos del alumno

NOMBRE: PABLO DE LA CRUZ RODRÍGUEZ

Datos del Trabajo

TÍTULO DEL PROYECTO:

Tribunal calificador

PRESIDENTE:

SECRETARIO:

VOCAL:

FDO.:

FDO.:

FDO.:

Reunido este tribunal el

/

/

, acuerda otorgar al Trabajo Fin de Grado presentado

por D./Dña.

 la calificación de

Dedicatoria

A mi familia, por acompañarme y apoyarme durante toda mi vida de manera incondicional.

Agradecimientos

Quiero agradecer a mi familia por haberme dado las oportunidades que he recibido a lo
largo de toda mi vida. También agradecerles el apoyo y comprensión en los momentos
difíciles.

Por otro lado, quería agradecer a mis tutores, por el esfuerzo y empeño que han
puesto en que este TFG salga adelante de la mejor manera posible, haciendo
innumerables revisiones y correcciones con tal de perfeccionar el trabajo.

Agradecer al CEU San Pablo por haberme brindado una formación íntegra con grandes
profesionales con los cuáles he podido formar vínculos personales que perdurarán más
allá de la finalización del grado.

Por último, agradecer a mis compañeros y amigos por hacer posible que la carrera haya
sido un disfrute y una etapa llena de momentos bonitos.

Resumen

El análisis automático de material videográfico deportivo ha pasado de ser un recurso

exclusivo de grandes clubes y cadenas de televisión a una necesidad generalizada en

formación, scouting semi-profesional. Muchas soluciones comerciales son cerradas,

costosas o exigen infraestructuras específicas (mallas de cámaras calibradas, tracking

propietario),

lo  que

limita  su  uso  para  clubes  modestos,  cuerpos  técnicos

independientes o entornos académicos.

Este  trabajo  presenta  TacticAI:  a  partir  de  vídeo  de  retransmisión  estándar  (sin

hardware adicional), el sistema obtiene información táctica en baja latencia mediante

procesamiento  por  micro-lotes  y  streaming  al  cliente  vía  WebSocket.  El  pipeline

combina:  (i)  detección  multiclase  (player,  ball,  referee,  goalkeeper)  con  modelos

YOLO  ajustados  al  dominio;  (ii)  seguimiento  multi-objeto  con  Re-ID  basado  en

embeddings  de  apariencia;  (iii)  clasificación  de  equipos  por  color  de  equipación

mediante agrupamiento cromático en el espacio CIELAB con votación temporal; (iv)

estimación determinista de posesión y pases; (v) proyección a coordenadas métricas

del campo mediante homografía estimada a partir de un detector de puntos clave del

terreno; (vi) mapas de calor de ocupación espacial por equipo; y (vii)  un motor de

predicción heurística de eventos tácticos con umbrales configurables, con narrativa

opcional en lenguaje natural generada por un modelo de lenguaje externo sin que

éste intervenga en el cálculo de las métricas.

La solución se integra en una interfaz web con actualización en tiempo casi real

(análisis en diferido incremental, no tiempo real estricto), una arquitectura de

trabajos asíncronos para entornos cloud con servicio API y proceso de análisis

desacoplado, contenerización mediante Docker con integración y despliegue

continuos, y capacidad de despliegue en plataformas cloud sin servidor.

El detector principal alcanza mAP@0.5 = 0.893 en el conjunto de test; el modelo de

keypoints  del  campo  alcanza  mAP@0.5  =  0.956.  El  pipeline  completo  opera  a

aproximadamente 60–65 ms por fotograma en GPU de gama media-alta (≈15–17 FPS

efectivos), procesando un vídeo en aproximadamente 1,5 veces su duración real.

Palabras clave: visión por computador, aprendizaje profundo, YOLO, re-identificación, homografía,

analítica deportiva, sistemas de apoyo a la decisión, tiempo casi real, arquitectura web asíncrona,
contenedores.

Abstract

The automated analysis of sports video has become an increasingly relevant tool at

all  levels  of  competition.  However,  leading  commercial  systems  —Tracab,  STATS

Edge,  InStat,  Wyscout—  require  proprietary  camera  rigs  and  licensing  budgets

beyond smaller clubs and independent coaching staff, limiting access to tactical data

to elite organisations.

This  bachelor's  thesis  presents  TacticAI:  a  computer-vision  system  that  extracts

tactical  information  —player  and  ball  positions,  team  assignment,  ball  possession,

pass events, and spatial heatmaps— directly from standard broadcast video, without

additional  hardware.  Results  are  delivered  incrementally  to  a  web  dashboard  via

WebSocket,  enabling  near-real-time  feedback  (incremental  deferred  analysis,  not

strict real-time) during or shortly after the match.

The pipeline combines: (i) multi-class object detection with fine-tuned YOLO models;

(ii)  multi-object  tracking  with  appearance-based  Re-ID;  (iii)  unsupervised  team

classification from kit colour; (iv) deterministic possession and pass estimation; and

(v)  homography-based  field  projection.  The  system  deploys  as  a  containerised

application (FastAPI, Docker) supporting local and Google Cloud Run deployment.

The main detector achieves mAP@0.5 = 0.893 on a domain-specific dataset of 9 621

images;  the  field-keypoint  model  reaches  mAP@0.5  =  0.956.  The  full  pipeline

operates at approximately 60–65 ms per frame on a mid-to-high-range GPU (≈15–17

effective  FPS),  processing  a  video  in  approximately  1.5×  its  real  duration,  with

incremental dashboard updates every 4–5 seconds.

Keywords:  computer  vision,  deep  learning,  YOLO,  re-identification,  homography,  sports  analytics,

decision support, near-real-time, asynchronous web architecture, containerisation.

Índice de contenidos

1. Introducción      13

1.1 Contexto del TFG
1.2 Objetivos
15
1.3 Usuarios del sistema y enfoque de procesamiento

13

16

2. Gestión del proyecto     17

2.1 Modelo de ciclo de vida
2.2 Planificación
2.3 Recursos necesarios
2.4 Justificación tecnológica y fundamentos teóricos

   18

   21

17

22

3. Análisis

24

24

3.1 Estado del arte
3.2 Especificación de requisitos
3.3 Diagrama de contexto     30
3.4 Casos de uso     30
3.5 Diagrama de secuencia     32

28

4. Diseño

34

4.1 Preparación del modelo YOLO y conjunto de datos
35
4.2 Arquitectura lógica
4.3 Diseño funcional
38
4.4 Arquitectura física y despliegue

45

34

5. Implementación y validación      50

5.1 Implementación del sistema
5.2 Pruebas automatizadas y CI
5.3 Métricas cuantitativas      57
5.4 Gestión de riesgos y ética

 50
 53

58

6. Conclusiones y líneas futuras     60

6.1 Conclusiones     60
6.2 Líneas futuras      61

Bibliografía

63

Uso de herramientas de inteligencia artificial generativa 67

Anexo A – Clases YOLO del sistema

68

Anexo B – Comandos de entrenamiento 69

Anexo C – Arranque local

70

Anexo D – Bitácora de ingeniería (iteraciones)  71

Anexo E – Glosario de términos  72

Anexo F – Conjuntos de datos y proceso de entrenamiento

73

Anexo G – Detalle técnico de los módulos de visión

Anexo H – Capa de servicios y despliegue (detalle)

77

86

Anexo I – Resultados completos de evaluación  89

19

Índice de figuras
Figura 1. Diagrama de Gantt.
Figura 2. Diagrama de contexto    30
Figura 3. Diagrama de casos de uso.
Figura 4. Diagrama de secuencia.
Figura 5. Vista lógica — cuatro capas.
Figura 6. Componentes del pipeline.
Figura 7. Ciclo de vida del estado del partido.
Figura 8. Vista de despliegue — local vs. GCP.
Figura 9. Flujo CI/CD.
Figura 10. Vista de carga de vídeo.
Figura 11. Dashboard de análisis.
Figura 12. Curvas de entrenamiento del detector YOLO11m
94
Figura 13. FPS del pipeline completo por configuración de hardware

31
33
35
38

52
52

44
47

49

95

Figura 1. D iagrama  de G ant t. .........................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................19

15

29

22
27

Índice de tablas
Tabla 1. Trazabilidad objetivos–requisitos–módulos.
Tabla 2. Bloques de trabajo y entregables.
18
Tabla 3. Planificación real vs. prevista.  19
21
Tabla 4. Recursos hardware.
Tabla 5. Recursos software.
21
Tabla 6. Estimación de costes cloud.
Tabla 7. Comparativa de soluciones.
Tabla 8. Requisitos funcionales.      28
Tabla 9. Requisitos no funcionales.
Tabla 10. Catálogo de datasets.     34
Tabla 11. Flujo de operación de los componentes de la Figura 5      39
Tabla 12. Relación capas–componentes–servicios.
Tabla 13. Comparativa de modos de despliegue.      46
Tabla 14. Pruebas de requisitos funcionales.
Tabla 15. Pruebas de requisitos no funcionales.     56
Tabla 16. Gestión de riesgos.
Tabla 17. Hiperparámetros del detector.     75
Tabla 18. Catálogo de módulos.  85
Tabla 19. Comparativa entre arquitectura monolítica y arquitectura desacoplada     88
Tabla 20. Variables de entorno.    88
Tabla 21. Métricas de evaluación del detector principal      91
Tabla 22. Métricas de evaluación del modelo de keypoints       92
Tabla 23. Benchmarks de rendimiento.

    93

55

45

58

Lista de acrónimos y siglas

Sigla

API

Significado

Application Programming Interface

CI/CD

Integración y entrega / despliegue continuos

CNN

COCO

CUDA

Red neuronal convolucional

Common Objects in Context (Lin et al., 2014)

Compute Unified Device Architecture (NVIDIA)

FastAPI

Framework web asíncrono para Python

FPS

GCP

GCS

GISI

GPU

IDF1

IoU

JSON

LLM

mAP

MOTA

NMS

Fotogramas por segundo (frames per second)

Google Cloud Platform

Google Cloud Storage

Grado en Ingeniería de Sistemas de Información

Unidad de procesamiento gráfico

Identity F1 Score (métrica de tracking)

Intersection over Union

JavaScript Object Notation

Large Language Model

mean Average Precision

Multiple Object Tracking Accuracy

Non-Maximum Suppression

Re-ID

Re-identificación

ROI

Región de interés

RANSAC

RANdom SAmple Consensus

REST

TFG

UI

Representational State Transfer

Trabajo Fin de Grado

Interfaz de usuario

12

Sigla

VRAM

WS

YAML

YOLO

Significado

Memoria de vídeo en GPU

WebSocket

Lenguaje de serialización legible por humanos

You Only Look Once (familia de detectores de objetos)

13

CAPÍTULO 1

Introducción

1.1 Contexto del TFG

El fútbol es, por volumen de audiencia y negocio, el deporte más seguido del mundo

[FIFA, 2022]. La digitalización de los últimos quince años ha convertido cada partido

en un archivo de datos masivo: retransmisiones completas a 50–60 fps, grabaciones

tácticas  de  cantera  a  ángulo  fijo,  clips  de  scouting  y  registros  GPS.  Procesar  e

interpretar  toda  esa  información  de  forma  manual  —marcando  manualmente

posiciones,  pases,  recuperaciones  y  líneas  defensivas—  es  un  proceso  que  puede

llevar horas para un único partido y que depende fuertemente de la experiencia y

subjetividad del analista.

La visión por computador ofrece una alternativa sistemática capaz de automatizar el

análisis  necesario.  A  partir  de  píxeles  de  vídeo  estándar  es  posible,  en  principio,

localizar  cada  entidad  relevante  (jugadores,  balón,  portero,  árbitro),  mantener  su

identidad  a  lo  largo  del  tiempo  mediante  tracking  multi-objeto,  proyectar  sus

posiciones a coordenadas métricas del terreno de juego y derivar automáticamente

las estadísticas que el cuerpo técnico necesita para tomar decisiones: porcentajes de

posesión,  mapas  de  calor  de  ocupación,  cadencias  de  pase,  señales  de  riesgo  de

pérdida de balón en zona peligrosa, etc.

Este proyecto parte de esa premisa y construye, desde cero, un sistema completo de

análisis  táctico  —  TacticAI  —  que  procesa  vídeo  de  retransmisión  estándar  (sin

hardware adicional) y entrega al cuerpo técnico información táctica en baja latencia

a través de una interfaz web accesible desde navegador.

1.1.1 Motivación técnica y práctica

Las  soluciones  comerciales  líderes  en  análisis  deportivo  automatizado  —Tracab

(ChyronHego) [31], STATS Edge [32], InStat, Wyscout y Hudl [33]— tienen en común

varios rasgos: utilizan redes de cámaras calibradas instaladas permanentemente en

el estadio, dependen de hardware propietario para la captura multi-ángulo, aplican

métodos de calibración manual o semi-automática del campo, y tienen modelos de

licencia anuales con costes de decenas de miles de euros. Este enfoque garantiza una

calidad de datos muy alta, pero impide el acceso a los segmentos más numerosos del

14

ecosistema  del  fútbol:  clubes  de  categorías  inferiores,  cuerpos  técnicos  de

academias, analistas independientes y entornos académicos de investigación.

Desde el punto de vista académico y de ingeniería, el proyecto tiene además un valor

intrínseco  como  integración  de  problemas  técnicos  de  primer  nivel  en  un  único

sistema coherente:

• Detección en escenas complejas: el fútbol representa uno de los dominios

más exigentes para la visión por computador: multitud de objetos similares

(22 jugadores con siluetas parecidas), oclusiones mutuas frecuentes, cambios

bruscos de zoom y ángulo de cámara, artefactos de compresión de vídeo y

variabilidad fotométrica alta (diferentes estadios, horas del día, condiciones

meteorológicas).

1.1.2 Tracking multi-objeto

• Calibración geométrica sin marcas artificiales: la estimación de la

homografía imagen-campo a partir de líneas y puntos naturales del terreno

de juego requiere modelos de keypoints robustos y procedimientos RANSAC

(acrónimo de Random Sample Consensus) — algoritmo iterativo de

estimación robusta de parámetros geométricos que descarta outliers de

forma estocástica; empleado aquí para ajustar la homografía imagen-campo

filtrando detecciones de keypoints ruidosas (Fischler & Bolles, 1981).

• Análisis de alto nivel a partir de señales de bajo nivel: convertir

coordenadas de bounding boxes (regiones rectangulares delimitadoras

que encuadran a cada objeto detectado en la imagen, definidas por las

coordenadas de su esquina superior izquierda y su anchura y altura) en

conceptos tácticos significativos (posesión, presión alta, transición

defensiva) requiere modelos heurísticos bien calibrados o aprendizaje

supervisado con etiquetas de difícil obtención.

• Despliegue  web  en  baja  latencia:  entregar  resultados  al  cliente  mientras  el

análisis  progresa  —en  lugar  de  esperar  al  final  del  vídeo—  requiere

arquitecturas asíncronas con streaming incremental.

La detección  de objetos, componente central de la visión por computador, resulta

especialmente adecuada para este problema. A diferencia de soluciones basadas en

15

sensores físicos, GPS o  redes de cámaras dedicadas, un detector de objetos opera

directamente sobre vídeo  de retransmisión estándar y puede, en  una sola pasada,

localizar y clasificar múltiples entidades —jugadores, porteros, árbitros y balón— sin

infraestructura  adicional.  Esta  capacidad  de  percepción  multiclase  hace  posible  la

automatización del análisis en el contexto de este TFG.

La arquitectura y componentes de la solución se describen en detalle en el Capítulo

4.

1.2 Objetivos

A  continuación,  se  presentan  el  objetivo  general  del  proyecto  y  su  desglose  en

objetivos  funcionales  y  no  funcionales.  La  correspondencia  entre  objetivos  y

componentes se recoge en la Tabla 1; los detalles de implementación se desarrollan

en el Capítulo 5.

1.2.1 Objetivo general

Desarrollar un sistema de análisis táctico en tiempo casi real (véase Anexo I para el

análisis  detallado  del  concepto  y  sus  matices)  basado  en  técnicas  de  visión  por

computador  capaz  de  generar  información  de  apoyo  a  la  decisión  para  el  cuerpo

técnico en fútbol, a partir de vídeo de retransmisión estándar.

Específicamente,  este  objetivo  general  se  desglosa  en  objetivos  funcionales  y  no

funcionales.

Objetivos funcionales ↔ implementación

Tabla 1. Trazabilidad objetivos ↔ requisitos ↔ módulos principales

#  Objetivo (resumen)

Estado

Criterio de aceptación

1  Detección +

Si — con matiz

mAP@0.5 ≥ 0,85 en test; identidad

seguimiento

en tiempo casi

real

"tiempo casi real"

mantenida en ≥ 80 % de secuencias.

2  Homografía y

Parcial —

Reproyección < 5 px en ≥ 70 % de

coordenadas métricas

condicionado a

fotogramas con campo visible.

visibilidad del campo

16

#  Objetivo (resumen)

Estado

Criterio de aceptación

3  Métricas tácticas

Si — núcleo completo;

Posesión con error < 5 %; pases con precisión

avanzadas

patrones avanzados

≥ 0,80.

parciales

4

Fine-tuning sobre

Si — a nivel

mAP@0.5 ≥ 0,85 en conjunto de validación

dataset propio

metodológico y de

del dataset propio.

ejecución

5

Recomendaciones

Parcial — alertas

≥ 3 tipos de alerta táctica configurables;

automáticas al

interpretables; no

narrativa coherente en ≥ 90 % de eventos.

entrenador

sistema estratégico

completo

Objetivos no funcionales ↔ implementación

#  Objetivo (resumen)

Estado

Criterio de aceptación

1  Aplicación

Si — interfaz web

integrada para

principal funcional

el cuerpo

técnico

2  Despliegue

Si – Despliegue en GCP

Interfaz accesible desde navegador estándar;
carga completa en < 3 s; dashboard
actualizable sin recargar.

Despliegue funcional en Cloud Run con
pipeline CI/CD operativo; servicio accesible
vía URL pública.

1.3 Usuarios del sistema y enfoque de procesamiento

TacticAI  es  una  solución  dirigida  a  cuerpos  técnicos,  analistas  juveniles  y  clubes

modestos que precisan métricas tácticas inmediatas (posesión, pases, heatmaps) sin

depender de costosas infraestructuras de hardware. Para satisfacer esta necesidad

sin comprometer la viabilidad técnica, el sistema delimita su alcance a un régimen de

procesamiento  de  baja  latencia  incremental,  descartando  el  tiempo  real  estricto

(cuyo desglose formal y análisis de niveles de temporalidad se detallan en el Anexo

I). El vídeo se analiza en micro-lotes de 3 segundos, enviando resultados progresivos

al dashboard web del usuario. Esta decisión de  diseño permite el  despliegue en la

nube  mediante  contenedores  automatizados,  un  requisito  clave  para  el  perfil

desarrollador (DevOps), lo que garantiza una arquitectura robusta, mantenible y de

alta trazabilidad metodológica.

17

CAPÍTULO 2

Gestión del proyecto

2.1 Modelo de ciclo de vida

Se adoptó un modelo de desarrollo iterativo e incremental, en lugar del clásico ciclo

en cascada. La principal razón es la naturaleza exploratoria del proyecto: en la fase

de inicio no era posible especificar con precisión los hiperparámetros del modelo de

detección,  la  arquitectura  de  tracking  ni  los  umbrales  del  motor  de  predicción,

porque estos aspectos y decisiones dependen de experimentos sobre datos reales.

Un  modelo  en  cascada  obligaría  a  congelar  el  diseño  antes  de  tener  suficiente

conocimiento del  dominio, con el riesgo de invertir semanas de desarrollo en una

dirección incorrecta.

El modelo iterativo permite, en cambio, validar cada capa técnica antes de añadir la

siguiente. Cada iteración produce un sistema funcional —aunque incompleto— que

puede ser evaluado y corregido. Los riesgos técnicos más altos (¿funciona el detector

en  vídeo  de  fútbol  real?  ¿es  estable  el  tracking  en  jugadas  de  área?)  se  afrontan

primero, antes de invertir en infraestructura web o cloud.

Las cinco iteraciones principales del desarrollo fueron:

1. Prototipo offline. Validación algorítmica sobre clips locales antes de

introducir servidor web ni cloud. Objetivo: comprobar que el detector YOLO

fine-tuneado combinado con el módulo de seguimiento con re-identificación

produce detecciones y trayectorias razonables en vídeo de fútbol real.

Duración: ~2 semanas.

2. Consolidación modular. El código del prototipo se refactoriza en módulos

reutilizables con interfaces claras: el motor de análisis por micro-lotes, el

módulo de seguimiento y el objeto de estado acumulable y serializable.

Esta iteración es la más importante desde el punto de vista de la

arquitectura de software: define las abstracciones sobre las que se

construirán todas las iteraciones posteriores.

3. Producto web monolítico. Integración de la solución en una aplicación web:

implementación del streaming WebSocket y diseño del dashboard

interactivo. El usuario puede por primera vez subir un vídeo desde el

18

navegador y ver resultados en tiempo casi real.

4. Arquitectura desacoplada. Para soportar despliegue en la nube con

múltiples trabajos concurrentes, se separa la capa web (API HTTP) del

servicio de análisis, introduciendo una cola de trabajos y un proveedor de

almacenamiento intercambiable.

Se introducen los conceptos de trabajo de análisis (job), cola de trabajos,

proveedor de almacenamiento intercambiable (sistema de ficheros local o

almacenamiento cloud) y gestión de migraciones de base de datos mediante

herramienta dedicada.

5. DevOps. Migración de los diferentes módulos de la aplicación a

contenedores, integración continua con tests automatizados en tres

versiones de Python, despliegue continuo automatizado en el entorno cloud.

Este enfoque iterativo explica por qué el repositorio contiene tanto el prototipo inicial

(modo  monolítico)  como  la  arquitectura  moderna  desacoplada.  Las  iteraciones

anteriores no se eliminan, sino que coexisten, lo que permite demostrar la evolución

del sistema y comparar las dos aproximaciones.

2.2 Planificación

Tabla 2. Bloques de trabajo y entregables asociados.

Fase (semanas
aprox.)
1–2

3–6

7–9

10–12

13–15

Bloque principal

Entregables clave

Inicio y definición

Primera inferencia YOLO, instalación de dependencias

Dataset y
entrenamiento

Conjunto de datos etiquetado, modelo de detección
entrenado

Tracking y
clasificación

ReID integrado, clasificador de equipos validado
cualitativamente

Micro-batching y
posesión

Bucle de análisis principal, posesión y pases
estabilizados

Homografía y
heatmaps

Detector de keypoints del campo, módulo de
calibración geométrica, filtros anti-artefacto

16–17

Motor de predicción  Motor heurístico de eventos; fichero de umbrales y

pesos; tests unitarios del módulo

18–19

Interfaz web

Producto monolítico con WebSocket, dashboard
interactivo y alertas en tiempo real

19

Fase (semanas
aprox.)
20–21

22–23

24–25

Bloque principal

Entregables clave

Dual API y worker

DevOps

Arquitectura desacoplada API + worker, migración de
BD, tests de integración
Docker, integración continua con tests automatizados,
despliegue cloud validado

Redacción y defensa  Memoria, presentación, vídeo demostración

Figura 1. Diagrama de Gantt — planificación orientativa del proyecto TacticAI.

2.2.1 Planificación real vs. prevista

El proyecto presentó desviaciones significativas respecto a la planificación inicial. La

Tabla 3 recoge, por fase,  la estimación de partida,  la duración real aproximada, la

desviación observada y la causa técnica principal que la explica. Las duraciones reales

se expresan en semanas aproximadas; para fechas exactas de cada iteración, véase la

Bitácora de ingeniería (Apéndice E).

Tabla 3. Planificación real vs. prevista.

Fase
Detector y
dataset

Est(s)  Real(s) Desviación  Causa técnica principal
4

+2 sem

6

Desequilibrio de clases (balón);
variabilidad fotométrica entre
estadios
Identity switches en oclusiones;
ajuste del buffer de tracks

Seguimiento con
re-identificación

3

5

+2 sem

Clasificación de
equipos

2

4

+2 sem

2

5

+3 sem

Calibración
geométrica /
homografía

Variaciones de iluminación;
confusión con portero;
inestabilidad temporal
Detección parcial de keypoints;
errores de proyección; diseño
de filtros anti-artefacto

Decisión tomada
Sobremuestreo del balón;
muestreo dirigido por
movimiento
Buffer temporal calibrado a
15–25 fotogramas;
combinación embedding +
IoU
Espacio CIELAB;
enmascarado césped y
dorsales; votación temporal
Umbral mínimo de inliers
RANSAC; fallback sin
proyección si hay pocos

Fase

Est(s)  Real(s) Desviación  Causa técnica principal

Mapas de calor y
análisis espacial

2

2

Sin
desviación

Dependencia de la homografía;
filtros de recorte al campo real

1

2

+1 sem

3

2

−1 sem

Procesamiento
incremental
(micro-lotes)

Arquitectura
cloud /
despliegue

Sincronización entre lotes y
WebSocket; consistencia del
estado acumulado

Buen soporte Docker y GCP;
CI/CD con GitHub Actions
relativamente directo

Flujo óptico
(evaluado,
descartado)
Validación y
redacción

1

0,5

3

4

Descartado Coste ~390 ms/fotograma
inviable para el pipeline en
tiempo casi real
Tests funcionales sobre vídeo
real; validaciones manuales de
homografía y fallback CPU

+1 sem

20

Decisión tomada
puntos

Módulo opcional; se
desactiva si la homografía no
está disponible
Motor de análisis por
micro-lotes desacoplado del
WebSocket
Cloud Run con escala a cero;
arquitectura desacoplada
capa web / servicio de
análisis
Desactivado por defecto;
disponible como opción
experimental
Combinación de pruebas
automatizadas, integración y
validación manual

Las  fases  que  superaron  ampliamente  la  estimación  fueron  principalmente  la

calibración geométrica campo-imagen y la clasificación de equipos:

La  calibración  geométrica  (homografía)  requirió  más  iteraciones  de  las  previstas:

detección parcial de keypoints en planos cerrados, errores de proyección con pocos

inliers RANSAC y filtros anti-artefacto añadidos progresivamente alargaron esta fase.

El  clasificador  de  equipos  también  superó  la  estimación:  las  variaciones  de

iluminación entre estadios obligaron a incorporar enmascarado del césped, exclusión

de dorsales, conversión a CIELAB y votación temporal, cada mejora validada sobre

vídeo real.

El flujo óptico se evaluó como respaldo del tracker pero su coste (~390 ms/fotograma)

lo hizo inviable en el pipeline activo; quedó desactivado por defecto.

La arquitectura desacoplada resultó más costosa de integrar de lo previsto, aunque

con beneficios claros en mantenibilidad y despliegue cloud; la integración en GCP fue,

en cambio, más rápida gracias al buen soporte documental.

Finalmente,  el  motor  de  alertas  tácticas  se  resolvió  mediante  heurísticas

configurables en lugar de un modelo supervisado, decisión que redujo el tiempo de

esta fase al eliminar la necesidad de un dataset de eventos tácticos etiquetados —de

muy alto coste de obtención— y que produjo un sistema más explicable y auditable.

21

2.3 Recursos necesarios

Tabla 4. Recursos hardware del proyecto.

Recurso

Especificación

Uso en el proyecto

GPU NVIDIA (≥ 6 GB VRAM

p. ej. RTX 3060 /

Entrenamiento YOLO,

recomendado)

RTX 4070

inferencia, extracción features

Re-ID

RAM sistema ≥ 16 GB

DDR4 / DDR5

Decodificación de vídeo y micro-lotes

Almacenamiento SSD ≥ 100 GB

NVMe preferible

Pesos .pt, datasets YOLO, vídeos de

prueba, outputs

CPU multi-núcleo

≥ 8 hilos

Preprocesado de vídeo, servidor web

Tabla 5. Recursos software (dependencias principales).

Propósito

Herramienta / versión

Lenguaje principal

Python 3.11

Detección y keypoints

Ultralytics YOLO (YOLOv8 / YOLO11)

Deep learning

PyTorch 2.x + CUDA 12.x

Visión por computador

OpenCV 4.x

Framework web

FastAPI + Uvicorn + Jinja2

Base de datos

SQLAlchemy + Alembic (SQLite / PostgreSQL)

Tests

pytest + pytest-asyncio + httpx

Contenedores

Docker + docker-compose

CI/CD

Cloud

GitHub Actions + Cloud Build (GCP)

GCP: Cloud Run, GCS, Pub/Sub (opcional)

LLM opcional

Anthropic Claude API

22

Tabla 6. Estimación de costes cloud (escenario de uso académico).

Servicio GCP

Uso

Coste estimado/mes

Cloud Run (CPU)

Servir API + UI, tráfico bajo

≈ 0 € (dentro de free tier)

Cloud Storage

Vídeos de prueba, artefactos ≈ 2 GB

≈ 0,04 €

Cloud SQL (opcional)

PostgreSQL producción

≈ 7 € (instancia micro)

Artifact Registry

Imagen Docker ≈ 1 GB

≈ 0,10 €

GPU VM (entrenamiento)

T4 · 10 h entrenamiento

≈ 3,50 € (puntual)

Total estimado (escenario académico)

≈ 11 € / mes

2.4 Justificación tecnológica y fundamentos teóricos

2.4.1 Elección del lenguaje y framework web

Python 3.11 es la opción más natural para este proyecto: los tres pilares del pipeline

—  PyTorch,  OpenCV  y  Ultralytics  YOLO—  ofrecen  bindings  Python  nativos,

ecosistema  activo  y  documentación  extensa.  Si  bien  existen  bindings  parciales  en

otros lenguajes, el ecosistema Python de deep learning en 2026 concentra la mayor

madurez de herramientas y comunidad.

FastAPI se elige frente a Flask o Django por tres razones concretas: (i) es ASGI-nativo,

lo  que  significa  que  el  servidor  puede  gestionar  WebSockets  y  peticiones  HTTP

concurrentes sin threading manual; (ii) la validación de entrada y salida se hace con

Pydantic,  lo  que  garantiza  que  los  contratos  de  datos  entre  API  y  cliente  son

verificables en tiempo de ejecución; (iii) genera documentación OpenAPI automática.

Uvicorn como servidor ASGI de producción ofrece rendimiento superior a Gunicorn

puro para cargas mixtas HTTP+WebSocket, con soporte nativo para asyncio.

2.4.2 Elección del framework de deep learning y detector

PyTorch 2.x es el framework de referencia para investigación y aplicaciones de visión

por computador, con soporte de primera clase en Ultralytics. Su modo de ejecución

eager  facilita  la  depuración  y  el  prototipado  rápido;  su  compilador  de  grafos

integrado  permite  optimizar  el  modelo  para  producción  sin  cambiar  el  código  de

23

entrenamiento.

Ultralytics YOLO se elige sobre otras implementaciones de YOLO (Darknet, YOLOv5

de Ultralytics, YOLOv7, RT-DETR) por su CLI unificada para entrenamiento, validación

y exportación, su integración directa con CUDA y su soporte de fine-tuning mediante

transfer learning desde checkpoints pre-entrenados en COCO. La versión YOLO11m

(medium)  ofrece  20M  parámetros  y  67.7  GFLOPs  —equilibrio  entre  calidad  de

detección y velocidad de inferencia en GPU de gama media.

2.4.3 Elección de infraestructura cloud

Google  Cloud  Platform  se  seleccionó  para  el  entorno  cloud  por  la  sencillez  de  su

interfaz de línea de comandos (gcloud), el nivel gratuito generoso para Cloud Run, y

la  integración  nativa  con  Cloud  Build  para  CI/CD.  Cloud  Run,  al  ser  serverless

orientado a contenedores, elimina la gestión de clústeres (Kubernetes) manteniendo

la portabilidad de Docker. Cloud Storage ofrece una API sencilla y costes mínimos para
almacenar vídeos de prueba y artefactos del modelo.

24

CAPÍTULO 3
Análisis

3.1 Estado del arte

3.1.1 Detección de objetos en vídeo deportivo

 La familia YOLO (You Only Look Once) (Redmon et al., 2016; Jocher et al., 2023) se ha

consolidado  como  el  estándar  de  facto  en  aplicaciones  de  tiempo  casi  real  por  su

mejor compromiso velocidad/precisión. SSD y RetinaFocal también se han utilizado

en deportes, pero YOLO11  ofrece actualmente resultados competitivos en objetos

pequeños y densamente agrupados, con ventaja en la relación velocidad/precisión

que requiere el procesamiento casi en tiempo real (véase Anexo F).

YOLO (You Only Look Once) realiza la detección y clasificación de objetos en una única

pasada de la red neuronal (single-shot detection), sin proponer regiones candidatas

en una primera etapa. Esto lo hace significativamente más rápido que detectores de

dos  etapas  (R-CNN,  Faster  R-CNN).  Tras  la  inferencia,  se  aplica  Non-Maximum

Suppression  (NMS):  procedimiento  post-inferencia  que  elimina  detecciones

duplicadas  solapadas,  manteniendo  solo  la  de  mayor  confianza  por  objeto,  lo  que

resulta  crítico  cuando  el  detector  genera  múltiples  cajas  por  jugador.  Para

especializar  el  modelo  al  dominio  futbolístico  se  emplea  transfer  learning:  se

inicializan los pesos de la red con un checkpoint pre-entrenado en COCO (Common

Objects in Context, Lin et al., 2014), un benchmark de referencia con más de 330 000

imágenes etiquetadas en 80 categorías que actúa como base  de  representaciones

visuales genéricas, y se ajustan sobre el dataset objetivo. Los primeros extractores de

características  ya  aprendidos  aceleran  la  convergencia  y  mejoran  la  precisión  con

datasets más pequeños.

3.1.2 Tracking multi-objeto

El  tracking  by  detection  se  implementa  tradicionalmente  con  el  algoritmo  SORT

(Bewley  et  al.,  2016),  que  combina  dos  mecanismos  complementarios:  el  filtro  de

Kalman (Kalman, 1960), que modela la trayectoria de cada jugador como un proceso

estocástico lineal y predice su posición en el fotograma siguiente a partir del estado

cinemático anterior (posición, velocidad), y el algoritmo húngaro (Kuhn, 1955), que

25

resuelve  el  problema  de  asignación  óptima  entre  las  predicciones  y  las  nuevas

detecciones minimizando el coste global (típicamente la distancia IoU entre cajas).

Cada jugador mantiene un identificador único mientras el solapamiento entre su caja

predicha  y  la  detectada  supere  un  umbral  configurable.  DeepSORT  añade  un

descriptor  de apariencia para  reducir  los identity switches cuando  los jugadores se

solapan.  ByteTrack  (Zhang  et  al.,  2022)  extiende  la  idea  utilizando  también  las

detecciones de baja confianza para evitar pérdidas en momentos de oclusión. BoT-

SORT y StrongSORT añaden correcciones de movimiento  de cámara (ECC) que son

especialmente  relevantes  en  fútbol  donde  la  cámara  sigue  la  jugada  con  pan-tilt-

zoom constante. TacticAI implementa un tracker ReID propio basado en extracción

de embeddings de apariencia con ventana temporal, adaptado a las características

específicas del dominio futbolístico.

3.1.3 Clasificación de equipos

La mayoría de los sistemas comerciales etiquetan los equipos manualmente al inicio

del partido. En la literatura académica se han explorado métodos de clustering por

color  de  equipación  (k-means  en  el  espacio  RGB  o  HSV)  (Donadello  et  al.,  2010;

Mahfuz et al., 2023), clasificadores CNN entrenados sobre ROIs de jugadores (Vats et

al.,  2019),  y  combinaciones  de  ambos.  La  dificultad  está  en  la  robustez  frente  a

variaciones  de  iluminación,  la  confusión  con  porteros  de  colores  distintos,  y  la

estabilidad  temporal  (los  jugadores  no  deben  cambiar  de  equipo  entre  batches).

TacticAI  usa  el  espacio  de  color  CIELAB  (Commission  Internationale  de  l'Éclairage,

1976)  con  máscaras  de  exclusión  para  el  verde  del  césped  y  los  dorsos  de  los

jugadores,  combinando  clustering  k-means  con  votación  temporal.  CIELAB  es  un

espacio  perceptualmente  uniforme  definido  por  tres  canales:  L*  (luminosidad),  a*

(eje verde-rojo) y b* (eje  azul-amarillo). A diferencia de RGB o  HSV, está diseñado

para que distancias euclídeas entre colores correspondan a diferencias perceptuales

similares  para  el  ojo  humano,  lo  que  lo  hace  especialmente  robusto  frente  a

variaciones de iluminación en escenas exteriores como el estadio.

3.1.4 Homografía imagen-campo

La  Homografía  consiste  en  una  transformación proyectiva 2D–2D descrita por una

matriz 3×3. Mapea puntos de la imagen de la cámara a coordenadas del plano del

26

campo  (y  viceversa),  permitiendo  medir  distancias  métricas  reales  a  partir  de

coordenadas en píxeles.

La estimación de la homografía en la práctica no puede realizarse mediante mínimos

cuadrados ordinarios, ya que las correspondencias entre keypoints del campo y sus

proyecciones  en

la

imagen  contienen

inevitablemente  outliers:  puntos  mal

detectados, oclusiones parciales de las líneas del terreno o artefactos de compresión

de vídeo. Para ello se emplea RANSAC (RANdom SAmple Consensus) (Fischler y Bolles,

1981),  un  algoritmo  de  estimación  robusta  que  opera  de  forma  iterativa:  en  cada

iteración  selecciona  aleatoriamente  un  subconjunto  mínimo  de  correspondencias

(cuatro pares de puntos para determinar la homografía 3×3), estima el modelo con

ese subconjunto, y calcula cuántas correspondencias restantes son inliers, es decir,

tienen un error de reproyección por debajo de un umbral. Tras un número suficiente

de iteraciones, se conserva el modelo con mayor consenso y se refina con todos sus

inliers  mediante  mínimos  cuadrados.  La  combinación  RANSAC  +  homografía  es  el

enfoque estándar en visión por computador para calibración de cámara en escenas

deportivas  (Hartley  y  Zisserman,  2004;  Homayounfar  et  al.,  2017)  y  resulta

especialmente  adecuada  para  fútbol,  donde  las  líneas  del  campo  proporcionan

correspondencias  densas  pero  ruidosas  a  causa  de  las  sombras,  los  jugadores  y  la

perspectiva variable de la cámara.

La  estimación  de  la  homografía  entre  la  imagen  de  la  cámara  y  el  modelo  2D  del

terreno  de  juego  se  ha  abordado  mediante  detección  de  líneas  (transformada  de

Hough), detección de puntos característicos del campo (esquinas, intersecciones del

círculo central) y más recientemente mediante modelos de detección de  keypoints

entrenados de forma supervisada. El trabajo de Homayounfar et al. (2017) estableció

las bases de la detección de layout del campo con CNNs; trabajos posteriores como

SoccerNet-Calibration  (CVPR  2021)  propusieron  benchmarks  estandarizados  para

este subproblema. TacticAI entrena un modelo YOLO11m como detector de 15 tipos

de puntos clave del campo, con mAP@0.5=0.956 (ver el Anexo I).

3.1.5 Análisis táctico automatizado

La extracción de eventos de alto nivel (pase, tiro, falta, fuera de juego) desde señales

de  visión  sigue  siendo  un  campo  activo.  SoccerNet  (CVPR  2022)  proporciona  un

benchmark para localización temporal de acciones en vídeo de fútbol. Modelos como

27

CALF  (Cioppa  et  al.,  2020)  y  E2E-Spot  (Hong  et  al.,  2022)  han  demostrado  alta

precisión  en  reconocimiento  de  acciones,  pero  dependen  de  datos  etiquetados

costosos. La solución objeto de este TFG, TacticAI, adopta un enfoque más sencillo y

explicable:  un  motor  heurístico  configurable  mediante  fichero  de  parámetros  que

puntúa  señales  tácticas  derivadas  de  posición  y  posesión,  sin  necesidad  de  datos

etiquetados de eventos.

3.1.6 Comparativa de soluciones actuales frente a TacticAI

A continuación, se recogen las principales limitaciones detectadas en las soluciones

existentes y la respuesta específica que ofrece TacticAI a cada una de ellas.

Limitación de soluciones
existentes

Soluciones representativas

Respuesta de TacticAI

Dependencia de hardware

Tracab, ChyronHego, Stats

Funciona sobre vídeo estándar

especializado (cámaras

Perform

de retransmisión, sin hardware

multiángulo, sensores GPS)

adicional

Coste prohibitivo para equipos

Opta, Second Spectrum

Arquitectura open-source

de categorías inferiores

desplegable en GPU de gama

media-alta

Identificación de equipos frágil

Sistemas basados en RGB/HSV

Espacio CIELAB con máscaras de

ante cambios de iluminación

exclusión del verde del césped;

clustering k-means con votación

temporal

Re-identificación de jugadores

Trackers genéricos (DeepSORT

Tracker ReID propio con

limitada tras oclusiones

estándar)

prolongadas

embeddings de apariencia y

ventana temporal, adaptado al

dominio futbolístico

Calibración del campo manual o

Soluciones comerciales clásicas

Detector YOLO11m de 15

con marcadores físicos

keypoints del campo (mAP@0.5

= 0,956)

Análisis táctico mediante

CALF, E2E-Spot, SoccerNet

Motor heurístico configurable

modelos supervisados con datos

etiquetados costosos

por fichero de parámetros, sin

necesidad de datos etiquetados

de eventos

28

Limitación de soluciones
existentes

Soluciones representativas

Respuesta de TacticAI

Opacidad: resultados sin

Modelos end-to-end de

Puntuación explícita de señales

explicabilidad para el cuerpo

aprendizaje profundo

tácticas derivadas de posición y

técnico

Tabla 7. Comparativa de soluciones.

posesión, con parámetros

interpretables

El  conjunto  de  estas  decisiones  técnicas  diferencia  a  TacticAI  de  los  sistemas

comerciales predominantes, ofreciendo una solución accesible, explicable y adaptada

a las restricciones reales de equipos de fútbol de categorías no profesionales.

3.2 Especificación de requisitos

El análisis de requisitos es la etapa previa al diseño y tiene como objetivo comprender

qué  debe  hacer  el  sistema  antes  de  decidir  cómo  lo  hará.  En  este  proyecto,  los

requisitos se derivaron de tres fuentes complementarias:

1. Análisis del dominio: estudio de las necesidades reales de un cuerpo

técnico de fútbol (¿qué métricas son útiles?, ¿con qué frecuencia se

necesitan?, ¿en qué formato?). Las entrevistas informales con técnicos de

equipos de categorías inferiores revelaron que posesión, pases, mapa de

ocupación del campo y alertas sobre presiones altas son las métricas más

demandadas.

2. Restricciones técnicas: el sistema debe funcionar sobre vídeo estándar

de retransmisión (sin hardware adicional), en hardware de consumo (GPU

de gama media-alta), y ser desplegable en la nube con coste controlado.

3. Objetivos académicos del Trabajo Fin de Grado: debe integrar de forma

consistente patrones tecnológicos que se utilicen en soluciones académicas

o industriales como, por ejemplo, Computer Vision o arquitecturas basadas

en microservicios, cumpliendo para ello los estándares formales del Trabajo

Fin de Grado definidos por la Universidad.

Los requisitos se documentan siguiendo el estándar IEEE 830, con identificador único,

descripción, componente responsable y criterio de aceptación. El cumplimiento de

cada requisito  fue  verificado  mediante  las  pruebas  unitarias  e  integración  del

repositorio (véase Sección 5.1) y mediante demostración sobre vídeo real.

29

3.2.1 Requisitos funcionales
Tabla 8. Requisitos funcionales del sistema.

ID

Descripción

Bloque funcional

RF1

Carga de vídeo vía navegador o ruta local

Capa web y API REST de carga

RF2  Detección YOLO en GPU/CPU configurable

(player, ball, referee, goalkeeper)

Motor de análisis por micro-lotes; pesos del
detector YOLO fine-tuneado

RF3

IDs persistentes para jugadores a través

Módulo de seguimiento con re-identificación

del vídeo

RF4

Asignación de equipo por apariencia

Clasificador de equipos por agrupamiento
cromático

RF5

Estimación de posesión y conteo de pases  Módulo de posesión y recuento de pases

RF6  Homografía, zonas y heatmaps opcionales  Módulo de calibración geométrica campo-imagen;

acumulador de mapas de densidad

RF7

Panel en tiempo casi real vía WebSocket

Producto web — capa de presentación
(WebSocket +  dashboard interactivo)

RF8

Predicción heurística de eventos y alertas  Motor de puntuación de eventos tácticos; fichero

de configuración de umbrales y pesos

RF9

Trabajo asíncrono (jobs) con

persistencia y cola

Gestor de trabajos asíncronos; proceso trabajador
independiente (worker)

3.2.2 Requisitos no funcionales

Tabla 9. Requisitos no funcionales.

ID

Descripción

Mecanismo de cumplimiento (descripción funcional)

RNF1

Rendimiento: micro-batching

para amortizar inferencia GPU

Tamaño de lote configurable en segundos; parámetro
de análisis ajustable por entorno

RNF2

Configurabilidad: variables de

entorno y YAML

Módulo de configuración centralizado por variables de
entorno (Pydantic Settings); fichero de umbrales
YAML configurable

RNF3

Portabilidad: fallback CPU si no hay

CUDA

Detección automática de GPU en tiempo de inicio;
ejecución en CPU como alternativa si no hay CUDA
disponible

30

ID

Descripción

Mecanismo de cumplimiento (descripción funcional)

RNF4  Mantenibilidad: tests de integración

en CI

Suite de tests automáticos ejecutada en el pipeline de
integración continua (CI/CD)

RNF5

Reproducibilidad: Docker +

Imágenes Docker con dependencias fijadas;

requirements.txt fijadas

fichero de dependencias con versiones

explícitas

RNF6

Resiliencia: reanudación de análisis

interrumpidos

Estado de análisis serializable con soporte de
reanudación desde el último lote completado

3.3 Diagrama de contexto

El diagrama de contexto delimita el sistema TacticAI respecto a sus actores externos

y  los  sistemas  con  los  que  interactúa.  Muestra  las  entradas  (vídeo  de  partido,

parámetros  de  análisis),  las  salidas  (estadísticas  tácticas,  heatmaps,  alertas)  y  las

interfaces con servicios externos. La relación entre componentes internos se detalla

en la Sección 4.1 (Visión general del sistema).

Figura 2. Diagrama de contexto

31

3.4 Casos de uso

El sistema TacticAI tiene dos actores principales:

• Analista / Cuerpo técnico: usuario principal del sistema. Interacciona con el

dashboard web para subir  vídeos, iniciar análisis y consultar  resultados. No

necesita conocimientos técnicos para operar el sistema una vez desplegado.

• DevOps  /  Administrador:  actor  técnico  responsable  de  desplegar  y

configurar el sistema. Interacciona con los ficheros de configuración, los

Dockerfiles y los pipelines de CI/CD.

Los cuatro casos de uso principales son:

• UC1 — Subir vídeo e iniciar análisis: el analista selecciona un fichero de vídeo

MP4, especifica los nombres de los equipos y la duración del micro-lote, y envía

el  formulario.  El  sistema  valida  el  fichero  (formato  y  tamaño  máximo),  lo

almacena  en  la  capa  de  almacenamiento  configurada,  crea  un  registro  del

trabajo en la base de datos con estado pendiente y encola el trabajo para su

procesamiento. El analista recibe confirmación inmediata con el identificador.

• UC2  —  Ver  estadísticas  en  tiempo  casi  real:  mientras  el  worker  procesa el

vídeo, el dashboard del analista recibe mensajes WebSocket con los resultados

incrementales  de  cada  micro-lote  (posesión  acumulada,  pases  por  equipo,

últimas alertas). Los gráficos del dashboard se actualizan automáticamente sin

necesidad de recargar la página.

• UC3  —  Consultar  heatmaps  y  alertas  tácticas:  al  finalizar  el  análisis  (o  en

cualquier momento durante el mismo), el analista puede consultar los mapas

de calor de ocupación del campo por equipo y el historial de alertas generadas

por  el  motor  heurístico.  Los mapas  de  calor  se  visualizan  superpuestos  al

modelo  2D  del  campo,  generados  a  partir  de  las  posiciones  proyectadas

durante el análisis.

• UC4 — Desplegar y configurar el servicio (actor: DevOps): el administrador

construye las imágenes Docker, configura las variables de entorno del servicio

(credenciales de almacenamiento, URL de base de datos y, opcionalmente,

clave de API del módulo de lenguaje natural), ejecuta las migraciones de base

de datos y despliega el servicio en la plataforma cloud mediante el pipeline de

integración y despliegue continuo. Este caso de uso no requiere la presencia

del analista.

32

•

Figura 3. Diagrama de casos de uso del sistema TacticAI.

La relación «include» indica que el caso de uso base siempre invoca al incluido como

parte obligatoria de su flujo. En el diagrama:

  UC2 «include» UC1:  Para ver  estadísticas  en  tiempo  casi  real es  obligatorio
primero subir vídeo e iniciar análisis — no hay estadísticas sin análisis previo.
  UC3 «include» UC2: Para consultar heatmaps y alertas el sistema ya tiene que

estar emitiendo datos en tiempo casi real (UC2 activo).

3.5 Diagrama de secuencia

El diagrama de secuencia describe el flujo de mensajes entre los cuatro participantes

principales del sistema durante el caso de uso UC1+UC2:

• Usuario (Browser): el analista usando la interfaz web en su navegador.

• Servidor web: expone los endpoints HTTP y WebSocket, valida peticiones y

coordina el inicio del análisis.

• Motor de análisis (micro-lotes): el núcleo analítico que procesa el vídeo en

lotes de duración configurable.

• YOLO / Módulos: los modelos de detección y el resto de módulos de análisis.

El flujo de interacción se divide en cuatro fases:

1.  Subida  del  vídeo  (HTTP POST):  el  navegador  envía  el  fichero  de  vídeo  y  los

parámetros de configuración mediante una petición HTTP.  FastAPI valida los

33

datos, guarda el fichero en la capa de almacenamiento y devuelve un job_id al

cliente. Esta fase usa HTTP síncrono porque la petición tiene un resultado claro

(éxito/fallo) en tiempos cortos (< 2 s para ficheros < 500 MB).

2.   Establecimiento  del  canal  WebSocket:  el  navegador  abre  inmediatamente

una  conexión  WebSocket  usando  el  job_id  recibido.  Esta  conexión  es

persistente: permanece abierta durante todo el análisis. El servidor web acepta

la conexión y lanza el análisis como tarea asíncrona en segundo plano.

3.  Ciclo  de  procesamiento  por  lotes  (motor  de  análisis):  el  motor  de  análisis

procesa el vídeo lote a lote. Para cada lote, el detector identifica objetos, el

módulo  de  seguimiento  asigna  IDs  persistentes,  el  clasificador  de  equipos

etiqueta cada track, el módulo de posesión calcula la posesión acumulada, y el

módulo geométrico acumula las posiciones proyectadas en el modelo 2D del

campo. El resultado del lote se serializa y se envía por WebSocket al navegador

como  mensaje  JSON.  El  navegador  actualiza  los  gráficos  y  estadísticas  del

dashboard sin recargar la página.

4.  Finalización (MatchState): cuando el motor de  análisis termina de procesar

todos  los  lotes,  envía  un  mensaje  de  control  al  WebSocket  indicando  la

finalización. El navegador muestra el estado final y cierra la conexión.

Figura 4. Diagrama de secuencia — subida de vídeo y análisis en tiempo real con WebSocket

34

      CAPÍTULO 4

   Diseño

1.
2.
3.
4.

4.1 Preparación del modelo YOLO y conjunto de datos

El detector que sostiene todo el pipeline de visión no se entrena desde cero, sino que

se especializa al dominio futbolístico mediante transfer learning sobre un checkpoint

YOLO11m pre-entrenado en COCO (Common Objects in Context). COCO aporta una

base de representaciones visuales genéricas —texturas, bordes y formas aprendidas

sobre más de 330 000 imágenes en 80 categorías— que actúa como punto de partida

de los pesos de la red. Sobre esa base se ejecuta el  fine-tuning con el conjunto de

datos  propio  descrito  en  la  sección  siguiente:  se  mantienen  los  extractores  de

características de las primeras capas, que ya capturan patrones visuales de bajo nivel,

y se reajustan las capas finales para reconocer las cuatro clases de interés del fútbol

(jugador,  balón,  portero  y  árbitro).  Partir  de  pesos  pre-entrenados  acelera  la

convergencia y permite alcanzar buena precisión con un dataset propio de tamaño

moderado,  evitando  el  coste  de  etiquetar  y  entrenar  sobre  cientos  de  miles  de

imágenes.

Para entrenar ambos modelos se construyó un conjunto de datos propio combinando

imágenes  de  SoccerNet  y  grabaciones  reales  de  partidos.  El  detector  principal  se

entrenó  sobre  9  621  imágenes  que  contienen  104  516  instancias  anotadas  en  las

cuatro clases del sistema (player, ball, referee, goalkeeper), con un reparto 70/15/15

para entrenamiento, validación y test, y augmentación mediante flips horizontales,

variaciones HSV y recorte aleatorio. El modelo de keypoints del campo se entrenó con

498 imágenes y 4 349 instancias, cada una con 32 puntos clave del terreno de juego,

capturadas en condiciones de iluminación y estadios variados.

El uso de datos propios responde a una limitación estructural de los datasets públicos

de  fútbol:  la  mayoría  están  capturados  con  cámaras  de  difusión  profesional  a

resolución y ángulo fijos, lo que introduce un sesgo que dificulta la generalización a

grabaciones  amateur  o  retransmisiones  con  encuadre  variable.  TacticAI  combina

imágenes de SoccerNet —el benchmark de referencia del dominio— con grabaciones

reales  para  cubrir  la  variabilidad  de  encuadres,  condiciones  de  iluminación  y

equipaciones. El catálogo completo de los datasets del sistema se recoge en la Tabla

10.

35

Tabla 10. Catálogo de datasets utilizados en TacticAI.

Dataset

Objetivo

Volumen y características

Dataset detector principal

SoccerNet + grabaciones reales

Entrenar YOLO11m para
detectar jugadores, balón,
portero y árbitro

9 621 imágenes · 104 516
instancias · 4 clases · Split
70/15/15 · augmentación: flips,
HSV, recorte

Dataset keypoints del campo

SoccerNet-Calibration + propio

Entrenar YOLO11-pose para
homografía mediante puntos
clave del terreno de juego

498 imágenes · 4 349 instancias ·
32 keypoints/imagen ·
Iluminación y estadios variados

COCO (Common Objects in
Context)

Pre-entrenamiento de los pesos
base (Microsoft, 2014)

~330 000 imágenes · 80
categorías · Solo como base de
fine-tuning; no se usa en
inferencia

El  resultado  del  entrenamiento  es  un  fichero  de  pesos  (checkpoint.pt)  que

constituye  el  artefacto  final  del  modelo.  Este  artefacto  se  empaqueta  como  un

recurso pasivo de la capa de Datos y Modelos: el sistema lo carga en memoria una

sola  vez  al  arrancar  el  motor  de  análisis  y  lo  reutiliza  para  inferir  sobre  todos  los

micro-lotes de fotogramas, sin volver a entrenar en tiempo de ejecución. El mismo

procedimiento de transfer learning y empaquetado se aplica al modelo de keypoints

del campo (YOLO11-pose), que parte igualmente de un checkpoint pre-entrenado y

se especializa para estimar los puntos clave del terreno de juego. El proceso completo

de  preparación  de  los  datos  y  ajuste  de  hiperparámetros  de  entrenamiento  se

documenta en el Anexo G.

4.2 Arquitectura lógica

Este capítulo describe el diseño de TacticAI desde sus distintos niveles de abstracción.

En  el  apartado  4.1  se  detalla  la  preparación  del  modelo  de  detección,  explicando

cómo  se  ha  realizado  el  transfer  learning  sobre  YOLO11  y  cómo  se  empaqueta  el

modelo  entrenado  para  su  consumo  por  el  sistema.  El  apartado  4.2  analiza  los

grandes bloques de la arquitectura lógica, organizando el sistema en cuatro capas

horizontales y describiendo los componentes de cada una. El apartado 4.3 desciende

al  diseño  funcional,  descomponiendo  la  capa  de  análisis  en  los  componentes  que

materializan el pipeline de visión y detallando, para cada uno, su responsabilidad y

su flujo de datos. El apartado 4.4 cierra con la arquitectura física y el despliegue.

El  sistema  se  estructura  en  cuatro  capas  lógicas  horizontales,  independizando  la

captura de datos de la lógica de negocio, la persistencia y la presentación.

36

Figura 5. Vista lógica de alto nivel del sistema TacticAI — cuatro capas.

Las  cuatro  capas  que  muestra  la  Figura  5  se  corresponden  directamente  con  los

participantes del diagrama de secuencia (ver Sección 3.5): el Browser actúa en la capa

de Presentación; el Servidor Web en  la capa de  Servicios; el Motor de análisis en la

capa de Análisis; y los modelos YOLO junto con el almacenamiento en la capa de Datos

y Modelos. A continuación, se describen los componentes principales de cada capa.

Capa de Presentación (Browser):

Implementada como una Single Page Application (SPA) que se ejecuta íntegramente

en el navegador del analista. Sus componentes principales son el formulario de subida

de  vídeo  (que  emite  el  HTTP  POST  inicial  del  diagrama  de  secuencia),  el  cliente

WebSocket  (que  mantiene  la  conexión  persistente  durante  todo  el  análisis  y  recibe

cada mensaje JSON de resultado parcial), y el dashboard de visualización (que actualiza

en  tiempo  real  los  gráficos  de  posesión,  heatmaps  y  alertas  tácticas  sin  recargar  la

página). Esta capa no tiene acceso directo a la base de datos ni a los modelos: toda

comunicación pasa por la capa de Servicios.

Capa de Servicios (Servidor Web):

Construida sobre FastAPI y Uvicorn, es el punto de entrada único del sistema. Expone

dos  tipos  de  interfaz:  endpoints  HTTP  REST  para  la  gestión  del  ciclo  de  vida  de  los

trabajos  (creación,  consulta  de  estado,  descarga  de  resultados)  y  un  endpoint

37

WebSocket que emite los resultados parciales según el motor de análisis los produce.

En el modo monolítico, esta capa lanza el análisis como tarea asíncrona en el mismo

proceso; en el modo distribuido, publica un mensaje en la cola Redis/Pub-Sub que el

worker  consume  de  forma  independiente.  La  capa  de  Servicios  actúa  como  árbitro:

valida todas las entradas (Pydantic), gestiona los UUID de job, y coordina el acceso a la

capa de Datos sin exponer rutas internas al cliente.

Capa de Análisis (motor de análisis):

Contiene  la  lógica  de  negocio  del  sistema.  El  componente  central  es  el  motor  de

análisis,  responsable  del  ciclo  de  procesamiento  por  lotes  descrito  en  la  fase  3  del

diagrama de secuencia:  divide el vídeo en micro-lotes de duración  configurable, los

procesa secuencialmente y serializa el resultado de cada lote en un mensaje JSON que

se envía por WebSocket. Dentro de cada lote, el motor de análisis orquesta la cadena

de  módulos  especializados:  el  detector  YOLO  identifica  objetos  frame  a  frame;  el

tracker asigna IDs persistentes entre frames mediante Re-ID; el clasificador de equipos

etiqueta cada track por color de equipación; el módulo de posesión calcula la posesión

acumulada; y el módulo geométrico proyecta las posiciones de los jugadores sobre el

modelo 2D del campo. El estado acumulado del partido (MatchState) persiste entre

lotes  y  constituye  la  memoria  del  análisis:  contiene  el  historial  de  posesión,  las

posiciones proyectadas y las alertas tácticas generadas hasta ese momento.

Capa de Datos y Modelos:

Agrupa  los  recursos  pasivos  que  las  capas  superiores  consumen.  Por  un  lado,  los

modelos de IA: el detector de jugadores y balón (YOLO11m entrenado sobre el dataset

propio descrito en la Sección 4.1), el modelo de keypoints del campo (YOLO11-pose) y,

opcionalmente,  el  motor  de  predicción  táctica.  Por  otro,  la  infraestructura  de

almacenamiento: el sistema de ficheros o bucket en la nube donde se depositan los

vídeos  subidos  y  los  resultados  finales,  la  base  de  datos  PostgreSQL  que  persiste  el

estado de cada  trabajo, y  la cola de mensajes Redis (solo en modo distribuido) que

desacopla  temporalmente  la  capa  de  Servicios  de  la  capa  de  Análisis.  Ningún

componente  de  esta  capa  inicia  comunicación:  responde  exclusivamente  a  las

peticiones de las capas superiores.

38

4.3 Diseño funcional

El  flujo  de  trabajo  de  TacticAI,  en  ambos  modos  de  operación,  sigue  cuatro  etapas

secuenciales que articulan el pipeline de análisis:

Ingesta  de  vídeo.  El  módulo  de  ingesta  abstrae  la  fuente  de  vídeo  (fichero  local,

almacenamiento  cloud  o  stream)  y  produce  micro-lotes  de  fotogramas  para

procesamiento incremental.

Detección, seguimiento y clasificación. El módulo de análisis por lotes procesa cada

micro-lote:  identifica  jugadores,  portero,  árbitro  y  balón;  mantiene  identidades

persistentes fotograma a fotograma; y asigna cada jugador a su equipo.

Análisis  espacial  y  métricas.  Con  objetos  identificados  y  proyectados  al  campo,  se

calcula posesión del balón, pases y mapas de calor por zona.

Entrega al cuerpo técnico. Los resultados de cada micro-lote se envían al dashboard

web de forma incremental vía WebSocket.

Cada  una  de  estas  etapas  se  implementa  mediante  los  componentes  funcionales

descritos a continuación.

Los  siete  componentes  funcionales  que  se  presentan  en  este  apartado  son  la

descomposición interna de la Capa de Análisis definida en la arquitectura lógica (véase

Sección 4.2): mientras aquella sección describe el sistema en cuatro capas horizontales

—Presentación, Servicios, Análisis y Datos y Modelos—, este apartado abre la Capa de

Análisis y detalla los componentes que el motor de análisis orquesta en su interior. El

núcleo analítico se organiza en los componentes funcionales numerados de la Figura

6. Cada componente cumple una función concreta dentro del procesamiento de cada

micro-lote; a continuación, se describe, para cada uno, qué hace, por qué es necesario

y qué aporta al sistema, remitiendo el detalle algorítmico al Anexo H.

La Figura 6 establece las dependencias entre componentes: cada uno consume la salida

del anterior, de modo que el pipeline se ejecuta de forma secuencial, del (1) al (7) sobre

cada micro-lote. Conviene recordar que estos componentes, están divididos entre las

4 capas definidas en la Sección 4.2.

39

Figura 6. Componentes del pipeline.

La Tabla 11 describe, para cada componente, qué recibe, qué hace, qué produce y de

qué componente depende.

Tabla 11. Flujo de operación de los componentes de la Figura 5: entradas, procesamiento, salidas y dependencias.

ID

(1)

(2)

(3)

Componente

Qué recibe

Qué hace

Qué produce

Depende de

Ingesta de
vídeo

Fuente de
vídeo (fichero,
cloud o stream)

Detección de
objetos

Fotogramas del
micro-lote

Seguimiento
(ReID)

Detecciones
por frame

Abstrae el
origen y trocea
el vídeo en
micro-lotes de
fotogramas

Localiza
jugador, balón,
portero y
árbitro con
YOLO11

Asigna
identificadores
persistentes
mediante
embeddings y
ventana
temporal

Micro-lotes de
fotogramas

— (origen del
pipeline)

(1)

(2)

Cajas de
detección por
clase y frame

Tracks con ID
estable entre
frames

40

ID

(4)

(5)

(6)

(7)

Componente

Qué recibe

Qué hace

Qué produce

Depende de

 Clasificación
de equipos

Tracks de
jugadores

Posesión y
pases

Proyección
geométrica

Predicción
táctica

Tracks
etiquetados y
posición del
balón

Posiciones en
píxeles y
keypoints del
campo

Posiciones,
posesión y
métricas
espaciales

(3)

Tracks
etiquetados
por equipo

(3), (4)

Estadísticas de
posesión y
circulación

Posiciones
métricas y
mapas de calor

(3); keypoints
del campo

Alertas tácticas
accionables

(5), (6)

Asigna cada
jugador a su
equipo por
color de
equipación
(CIELAB)

Estima
poseedor del
balón y registra
pases y
recuperaciones
por proximidad

Proyecta a
coordenadas
reales
mediante
homografía
(opcional)

Evalúa señales
y genera
alertas tácticas
explicables

A  continuación,  se  detalla  el  objeto  y  funcionamiento  de  cada  componente.  No

obstante, lo anterior, el Anexo H contiene el detalle del diseño de cada uno de estos

componentes,  el  detalle  de  implementación  y  su  trazabilidad  con  los  requisitos

funcionales.

4.3.1  Descripción de los componentes

Para cada componente se describe su función, necesidad y aportación al sistema. El

detalle algorítmico, los hiperparámetros, los umbrales adoptados y la trazabilidad con

los requisitos funcionales de todos los componentes se recogen en el Anexo H.

(1) Ingesta de vídeo

El componente (1) abstrae el origen del vídeo —fichero local, almacenamiento en la

nube  o  stream  en  directo—  y  lo  entrega  al  resto  del  pipeline  en  micro-lotes  de

fotogramas de tamaño configurable. Esta abstracción es necesaria para independizar

el  análisis  de  la  procedencia  del  vídeo  y,  al  mismo  tiempo,  para  habilitar  el

procesamiento incremental: en lugar de esperar a que termine el partido, el sistema

empieza  a  producir  resultados  en  cuanto  completa  el  primer  lote.  Internamente,  el

41

módulo emplea decodificación eficiente frame a frame mediante OpenCV y aplica un

mecanismo de muestreo adaptativo que permite saltar fotogramas cuando la carga de

la GPU satura el pipeline, priorizando la continuidad del análisis sobre la exhaustividad.

El  tamaño  del  micro-lote  es  un  parámetro  con  impacto  directo  en  la  latencia  de

actualización del dashboard y en la eficiencia del batch de inferencia de YOLO.

(2) Detección de objetos

El componente (2) localiza en cada fotograma las cuatro clases de interés —jugador,

balón, portero y árbitro— mediante el detector YOLO11m especializado por *transfer

learning* sobre el dataset propio descrito en §4.1. Es la base imprescindible de todo el

análisis posterior: sin detecciones fiables no hay seguimiento, posesión ni métricas. La

elección de una arquitectura de detección en una sola pasada (*single-shot*) frente a

detectores de dos etapas responde a la necesidad de mantener la inferencia por debajo

de los 40 ms por micro-lote; el modelo produce, para cada detección, una bounding

box  con  sus  cuatro  coordenadas,  una  puntuación  de  confianza  y  la  clase  predicha.

Sobre estas salidas se aplica supresión no máxima (NMS) para eliminar cajas solapadas

y un filtro por umbral de confianza configurable que permite ajustar el equilibrio entre

precisión y exhaustividad según el contexto del partido.

(3) Seguimiento multi-objeto (ReID)

El  componente  (3)  asigna  a  cada  objeto  detectado  un  identificador  persistente

fotograma a fotograma, manteniéndolo aunque el jugador se solape con otros, salga

del encuadre temporalmente o quede parcialmente ocluido. Sin este componente,

cada fotograma produciría detecciones anónimas y sería imposible atribuir posesión,

pases o trayectorias a un jugador concreto. El seguimiento combina dos fuentes de

información  complementarias:  la  similitud  de  apariencia,  calculada  mediante

embeddings visuales que comparan el vector de características de cada detección

con los tracks activos usando distancia coseno; y la coherencia espacial, medida con

Intersect-over-Union (IoU) entre bounding boxes consecutivas. La asociación óptima

entre  detecciones  y  tracks  se  resuelve  con  el  algoritmo  húngaro,  que  minimiza  el

coste global de asignación en un solo paso. Para gestionar desapariciones breves, se

mantiene  una  ventana  de  pérdida  configurable  antes  de  cerrar  un  track

definitivamente.

42

(4) Clasificación de equipos

El componente (4) asigna cada jugador detectado a uno de los dos equipos a partir

del  color  dominante  de  su  equipación.  Es  necesario  para  que  todas  las  métricas

tácticas  —posesión,  pases,  ocupación  del  campo,  presiones—  tengan  sentido

diferenciado por equipo; sin esta clasificación, el sistema solo produciría estadísticas

agregadas sin valor táctico. La cadena de procesamiento encadena cuatro pasos: (i)

extracción  del  ROI  del  torso  sobre  la  bounding  box  de  cada  jugador,  recortando

deliberadamente las piernas y los pies para excluir el color del césped y las medias,

que  introducirían  ruido  en  la  caracterización;  (ii)  aplicación  de  una  máscara  de

exclusión  que  elimina  los  píxeles  de  césped  (verde)  y  fondo  no  uniforme,

garantizando  que solo  la tela  de la camiseta contribuye a  la muestra  de color; (iii)

extracción de características en el espacio perceptualmente uniforme CIELAB, cuya

separación  de  luminancia  y  crominancia  aporta  robustez  ante  los  cambios  de

iluminación entre estadios, horas del día y condiciones meteorológicas, a diferencia

del  espacio  RGB  o  HSV;  y  (iv)  clustering  con  K-medias  (k=2,  uno  por  equipo)  para

agrupar  automáticamente  las  camisetas  en  dos  clases  de  color  sin  necesidad  de

configuración  previa  del  usuario,  seguido  de  una  votación  temporal  por  mayoría

sobre los últimos N fotogramas que estabiliza la etiqueta y evita cambios de equipo

entre  fotogramas  consecutivos  debidos  a  oclusiones  parciales  o  variaciones

momentáneas de iluminación.

(5) Estimación de posesión y pases

El componente (5) estima, en cada fotograma, qué jugador posee el balón y registra

los  eventos  de  pase  y  recuperación.  Es  necesario  para  producir  las  estadísticas  de

posesión y circulación del balón que el cuerpo técnico necesita para evaluar el control

del juego, la presión sobre el rival y la capacidad de progresión; sin este componente,

el sistema sería ciego a quién domina el partido. La asignación de posesión se realiza

mediante un modelo de proximidad euclidiana que identifica al jugador más cercano

al centroide del balón en cada frame y lo declara poseedor si su distancia en píxeles

está por debajo de un umbral adaptativo calibrado en función del tamaño aparente

de los jugadores en la imagen. Para evitar que las disputas —momentos en los que

varios jugadores compiten por el balón a distancias similares— produzcan cambios

de poseedor erráticos fotograma a fotograma, se aplica una histéresis temporal: el

poseedor  no  cambia  hasta  que  un  nuevo  candidato  mantiene  la  mínima  distancia

43

durante al menos M fotogramas consecutivos. Un pase se registra cuando la posesión

cambia  entre  dos  jugadores  del  mismo  equipo;  una  recuperación,  cuando  cambia

entre equipos distintos. Las estadísticas se acumulan en el MatchState y se envían al

dashboard al final de cada micro-lote.

(6) Proyección geométrica

El  componente (6) transforma las  posiciones  de  los jugadores desde el espacio  de

píxeles de la imagen captada por la cámara al sistema de coordenadas métricas del

terreno de juego. Esta transformación es necesaria para obtener métricas espaciales

con  significado  táctico  real  —distancias  entre  jugadores,  amplitud  de  líneas,

profundidad del bloque defensivo— y para generar los mapas de calor proyectados

sobre  el  modelo  2D  normalizado  del  campo;  sin  ella,  las  posiciones  son  meras

coordenadas  de  píxel  sin  escala  ni  alineación  con  el  terreno.  La  transformación  se

modela como una homografía planar (matriz H de 3×3) que relaciona los puntos del

plano imagen con los del plano del campo. Para estimarla, el modelo de  keypoints

YOLO11-pose —entrenado sobre el dataset SoccerNet-Calibration con 32 puntos de

referencia del campo— detecta las marcas del terreno visibles en cada fotograma; a

partir de esas correspondencias imagen-campo, la matriz H se calcula con el algoritmo

RANSAC  (*Random  Sample  Consensus*),  que  descarta  automáticamente

las

correspondencias erróneas (*outliers*) debidas a oclusiones o errores de detección,

proporcionando una estimación robusta incluso cuando parte de las líneas del campo

no son visibles. Sobre la homografía resultante se aplican filtros anti-artefacto que

detectan y descartan proyecciones fuera  de los límites del campo o con distorsión

excesiva, evitando que los mapas de calor presenten puntos espurios. El componente

es opcional: si se desactiva, el resto del pipeline sigue funcionando sin coordenadas

métricas.

(7) Motor de predicción táctica de eventos

El  componente  (7)  es  el  nivel  más  alto  de  abstracción  del  pipeline:  transforma  los

datos  crudos  de  posición,  posesión  y  métricas  espaciales  en  alertas  tácticas

accionables  —presión  alta,  oportunidad  de  contragolpe,  bloque  bajo  defensivo—

directamente  útiles  para  el  cuerpo  técnico.  Es  necesario  porque  los  datos  de  bajo

nivel  (coordenadas,  IDs,  porcentajes)  no  son  directamente  interpretables  por  un

entrenador en tiempo de partido; el valor del sistema reside precisamente en esta

capa de interpretación. El motor evalúa, en cada micro-lote, un conjunto de señales

tácticas —como el número de jugadores del equipo  rival en el tercio defensivo, la

44

velocidad de transición posesiva o la amplitud del bloque— y las combina mediante

una función de puntuación ponderada para calcular un índice de riesgo/oportunidad

por tipo de evento. Cuando ese índice supera un umbral predefinido, se emite una

alerta. Para evitar spam de notificaciones, se aplica un mecanismo de cooldown que

impide que el mismo tipo de alerta se repita antes de un mínimo de fotogramas. La

arquitectura es deliberadamente determinísta y explicable: los pesos y umbrales son

parámetros  configurables,  no  parámetros  aprendidos  de  una  caja  negra,  lo  que

permite  al  entrenador  entender  y  validar  por  qué  se  emitió  cada  alerta.

Opcionalmente, un modelo de lenguaje (*LLM*) reformula la alerta cuantificada en

lenguaje natural comprensible; en ningún caso decide por sí mismo —la decisión ya

está  tomada  determinísticamente  antes  de  invocarle—,  lo  que  garantiza  la

trazabilidad y evita alucinaciones que podrían desorientar al cuerpo técnico.

4.3.2 Estado del partido y ciclo de vida del análisis

El  motor  de  análisis  mantiene  un  objeto  MatchState  que  actúa  como  memoria

compartida  entre  los  siete  componentes  del  pipeline  de  esta  sección.  Cada

componente  escribe  en  él  al  término  de  su  ejecución  dentro  del  micro-lote:  el

detector  (2)  registra  las  detecciones  brutas  del  frame;  el  tracker  (3)  añade  los

identificadores persistentes; el clasificador (4) etiqueta cada track con su equipo; el

módulo de posesión (5) actualiza el porcentaje acumulado y el historial de pases; la

proyección geométrica (6) almacena las coordenadas de campo; y el motor táctico (7)

añade las alertas generadas. Al final de cada lote, este MatchState se serializa y se

envía al dashboard vía websocket. Esto garantiza que el dashboard reciba siempre un

contexto completo y coherente —incluyendo todos los estados parciales acumulados

por los micro-lotes anteriores— independientemente del momento en que el usuario

se conecte.

Figura 7. Ciclo de vida del estado del partido.

45

4.4 Arquitectura física y despliegue

TacticAI es un sistema de análisis táctico sobre vídeo de retransmisión estándar, sin

necesidad de hardware especial ni cámaras adicionales. El usuario —o un operador

de análisis— sube un fichero de vídeo al sistema a través de un navegador web, y en

cuestión  de  minutos  recibe,  de  forma  incremental  vía  WebSocket,  estadísticas

tácticas actualizadas conforme el análisis progresa en el servidor.

4.4.1 Arquitectura física

En el despliegue en la nube, todos los elementos del sistema residen en un  único

proyecto  de  Google  Cloud  Platform,  alojado  en  la  región  europe-west1.  Los

elementos físicos que existen son los siguientes. El navegador del analista actúa como

cliente externo y es el único punto de contacto del usuario con el sistema. La entrada

al backend se realiza a través de un servicio  de  Cloud Run  que ejecuta  la API web

(FastAPI): recibe la subida del vídeo, gestiona el ciclo de vida del trabajo y mantiene

abierta la conexión WebSocket con el navegador. El desacoplo entre la recepción del

trabajo y su procesamiento se materializa mediante Pub/Sub: la API publica el trabajo

y el worker  lo consume de forma asíncrona. El  núcleo de cómputo es  un segundo

servicio de Cloud Run con GPU que ejecuta el worker de inferencia; este analiza el

vídeo por micro-lotes (batches) y, al completar cada lote, publica el resultado parcial,

de modo que el dashboard se actualiza de forma incremental sin esperar al final del

partido. La persistencia se reparte entre Cloud Storage (GCS), donde se depositan los

vídeos subidos y los resultados, y Cloud SQL (PostgreSQL), que guarda el estado de

cada trabajo. Los pesos de los modelos YOLO viajan dentro de la imagen del worker,

que  se  almacena  en  Artifact  Registry,  y  las  credenciales  se  custodian  en  Secret

Manager y se inyectan como variables de entorno en tiempo de ejecución. La Figura

8 muestra esta vista física, contrastando el entorno local con el despliegue en Google

Cloud.

4.4.2 Modos de despliegue

La arquitectura del sistema combina dos modos de operación, según el entorno de

despliegue y el número de usuarios concurrentes:

       • Modo de ejecución monolítico: la API web gestiona el análisis directamente en

un proceso de fondo. Adecuado para demostración y uso local.

       • Modo  de  ejecución  distribuido:  la  capa  de  API  (gestión  de  trabajos)  se

46

desacopla  del  proceso  de  análisis,  permitiendo  despliegue  cloud  y  análisis

simultáneos.

El modo monolítico es la opción recomendada para desarrollo local, demostraciones

y entornos con un único usuario: no requiere infraestructura adicional (y se arranca

con  un  solo  comando.  El  modo  distribuido  es  necesario  en  cuanto  hay  más  de  un

análisis  simultáneo  o  se  despliega  en  la  nube:  la  API  responde  en  milisegundos

mientras el worker procesa el vídeo en segundo plano, y la comunicación incremental

por  WebSocket  mantiene  el  dashboard  actualizado  en  tiempo  real.  Ambos  modos

comparten el mismo núcleo analítico; la elección solo afecta a la capa de servicios.

La  siguiente  tabla  relaciona  cada  capa  lógica  con  su  componente  lógico,  el

componente del runtime y el servicio de GCP sobre el que se despliega.

Tabla 12. Relación entre capas lógicas, componentes de runtime y servicios de Google Cloud Platform.

Capa lógica

Componente lógico

Componente del
runtime

Servicio / infra
de GCP

Relación de
despliegue

Presentación

Dashboard / SPA
(cliente)

HTML + JS servido como
estático

Cloud Run
(servicio web)

Servicios

API de gestión de
trabajos

FastAPI + Uvicorn
(Dockerfile.web)

Cloud Run
(servicio web)

Servicios

Desacoplo API-análisis

Cola de mensajes

Pub/Sub

Análisis

Motor de análisis

Worker de inferencia
(Dockerfile.worker,
PyTorch+CUDA)

Cloud Run con
GPU

Datos y Modelos

Almacenamiento de
vídeos y resultados

Cliente de objetos

Cloud Storage
(GCS)

Datos y Modelos

Estado de los trabajos

ORM / cliente SQL

Cloud SQL
(PostgreSQL)

Datos y Modelos  Modelos YOLO (pesos

.pt)

Ficheros embebidos en la
imagen

Artifact Registry

Transversal

Gestión de secretos

Variables de entorno del
contenedor

Secret Manager

Servido por el
contenedor de la API; se
entrega al navegador del
analista

La imagen
Dockerfile.web se
despliega en Cloud Run;
expone REST y
WebSocket

La API publica el job en
Pub/Sub; el worker lo
consume de forma
asíncrona

La imagen
Dockerfile.worker
se despliega como
servicio Cloud Run con
GPU que consume
Pub/Sub

El worker lee el vídeo y
escribe resultados en un
bucket GCS por job_id

Persiste el estado de
cada job; accesible desde
API y worker

Los pesos se copian en
Dockerfile.worker;
la imagen se publica en
Artifact Registry

Las credenciales se
inyectan en tiempo de
ejecución desde Secret
Manager

47

Tabla 13. Comparativa de modos de despliegue.

Aspecto

Entorno objetivo

Modo monolítico (local)

Modo distribuido (Google Cloud)

Desarrollo, demostración, un único
usuario

Producción cloud, múltiples análisis
simultáneos

Capa de servicios

API y análisis en el mismo proceso

API (Cloud Run) desacoplada del
worker vía Pub/Sub

Cómputo de análisis

Persistencia

Cola de mensajes

Contenedores

Tarea de fondo en el mismo
contenedor

Worker dedicado en Cloud Run con
GPU

PostgreSQL y ficheros locales
(docker-compose)

Cloud SQL (PostgreSQL) + Cloud
Storage (GCS)

No requerida

Pub/Sub

Dockerfile.legacy (docker-compose
up)

Dockerfile.web +
Dockerfile.worker en Artifact
Registry

Despliegue automatizado vía Cloud
Build (CI/CD)

Horizontal: varios workers en
paralelo

Arranque

Un solo comando, sin
infraestructura adicional

Escalabilidad

Limitada a un análisis a la vez

4.4.3 Aplicación web y capa de servicios

La  infraestructura  de  TacticAI  está  automatizada  mediante  scripts  de  despliegue  y

pipelines  de  CI/CD  versionados  en  el  repositorio.  Todos  los  recursos  GCP  se

aprovisionan con el  script  create_gcp_resources.sh, lo que  permite  reproducir el

entorno desde cero sin pasos manuales.

Figura 8. Vista de despliegue — entorno local (izquierda) vs. Google Cloud Platform (derecha).

48

4.4.4 Creación de contenedores con Docker

El sistema se distribuye como imágenes Docker, no como dependencias instaladas en

el  sistema  operativo  del  servidor.  Esto  garantiza  que  el  comportamiento  en

producción  (Google  Cloud  Run)  sea  idéntico  al  comportamiento  en  el  entorno  de

desarrollo  local,  eliminando  la  clase  de  errores  «funciona  en  mi  máquina».  El

repositorio contiene tres Dockerfiles:

• Dockerfile.web: imagen de la API del servidor web. Imagen base Python

3.11-slim, instala dependencias sin PyTorch (la API no ejecuta inferencia),

configura Uvicorn como entrypoint.

• Dockerfile.worker: imagen del worker de análisis. Imagen base Python

3.11-slim con soporte CUDA (para GPU), instala PyTorch + Ultralytics +

OpenCV, copia los pesos del modelo YOLO.

• Dockerfile.legacy (o Dockerfile): imagen de la aplicación

monolítica de demostración, para uso local.

El fichero docker-compose.yml orquesta todos los servicios en local —web (puerto

8000), worker, base de datos PostgreSQL y Redis—; con un único comando (docker

compose up) el sistema completo está operativo en minutos.

4.4.5 Seguridad

La seguridad en un sistema que procesa vídeos privados de equipos deportivos es un

requisito no negociable. Los principios de seguridad aplicados son:

• Secretos fuera del código: ninguna credencial, clave de API ni contraseña

aparece en el código fuente del repositorio. Todos los secretos se inyectan

como variables de entorno en tiempo de ejecución; en Cloud Run se

almacenan en Google Secret Manager y se montan como variables de

entorno del contenedor. El fichero .env de desarrollo local está en

.gitignore y nunca se versiona.

• Principio de mínimo privilegio en IAM: la cuenta de servicio del worker

tiene permisos de lectura/escritura solo en el bucket GCS de vídeos de ese

job, no en todos los buckets del proyecto. La API web tiene solo permisos

para publicar en la cola Pub/Sub.

• Cloud Run con autenticación: en producción, los endpoints de Cloud Run se

configuran con  --no-allow-unauthenticated . El acceso externo se realiza a

49

través de un proxy o un token de identidad OAuth2, no directamente.

• Validación de rutas de fichero: antes de abrir o escribir cualquier fichero, la

ruta se valida para detectar ataques de path traversal (por ejemplo, un

nombre de fichero que contiene ../../../etc/passwd). FastAPI y Pydantic

validan los campos de entrada en todos los endpoints.

• Aislamiento de datos entre jobs: cada job tiene un UUID único. Los ficheros

de vídeo, los resultados parciales y el estado final se almacenan en sub-paths

que incluyen el job_id, impidiendo que un usuario acceda a los datos de otro

job si no conoce su UUID.

4.4.6 CI/CD

El  pipeline  de  integración  y  entrega  continua  (CI/CD)  automatiza  dos  procesos

distintos: la integración continua (CI), que verifica que cada cambio en el código no

rompe

los  tests  existentes,  y

la  entrega  continua

(CD),  que  despliega

automáticamente los cambios aprobados a producción.

GitHub  Actions  (CI):  se  ejecuta  en  cada  push  y  en  cada  pull  request.  El  workflow

ci.yml instala las dependencias, ejecuta el conjunto de tests unitarios e integración

(pytest tests/) y reporta los resultados en la interfaz de GitHub. Si los tests fallan, el

PR no puede aprobarse ni fusionarse.

Cloud Build (CD): se activa solo en pushes a la rama main (es decir, solo después de

que  un  PR  ha  sido  revisado  y  aprobado).  El  trigger  de  Cloud  Build  construye  las

imágenes Docker, las publica en Artifact Registry y despliega las nuevas imágenes en

Cloud  Run.  El  proceso  completo  de  build  y  despliegue  tarda  típicamente  de  3  a  5

minutos.

Figura 9. Flujo CI/CD — desde push en GitHub hasta despliegue en Cloud Run vía GitHub Actions y Cloud Build.

50

          CAPÍTULO 5

     Implementación y validación

5.1 Implementación del sistema

5.1.1 Repositorio y acceso al sistema desplegado

El  código  fuente  completo  de  TacticAI  es  público  y  está  disponible  en  el  siguiente

repositorio de GitHub:

https://github.com/Pablodlx/TacticAI.git

La  aplicación  está  también  desplegada  y  accesible  en  la  siguiente  URL  de  Google

Cloud Run:

https://tacticai-web-956093206862.europe-west1.run.app/

5.1.2 Estructura del repositorio y módulos principales

El repositorio sigue una estructura monorepo que agrupa en un único directorio raíz

el backend de análisis, la API web y los ficheros de configuración de infraestructura.

Esta organización facilita el desarrollo conjunto de los distintos módulos y permite

lanzar el sistema completo con un único comando Docker Compose. Los directorios y

ficheros principales son los siguientes:

TacticAI/
├── api/                     # Capa de Servicios: API web FastAPI + WebSocket
│   ├── main.py              # Punto de entrada: endpoints REST y WebSocket
│   ├── job_manager.py       # Gestión del ciclo de vida de trabajos (UUID,
estado)
│   └── schemas.py           # Modelos Pydantic para validación de E/S
├── worker/                  # Motor de análisis
│   ├── batch_processor.py   # Orquestador principal del pipeline de visión
│   ├── tracker.py           # Seguimiento multi-objeto (ReID)
│   ├── team_classifier.py   # Clasificación de equipos (CIELAB + K-medias)
│   ├── possession.py        # Estimación de posesión y detección de pases
│   ├── homography.py        # Proyección geométrica (RANSAC + filtros)
│   └── tactical_engine.py   # Motor de alertas tácticas
├── frontend/                # SPA (Single Page Application) en HTML/CSS/JS
│   ├── index.html           # Página principal: formulario de carga +
dashboard
│   ├── app.js               # Lógica de la SPA: WebSocket, actualización del
UI
│   └── styles.css           # Estilos del dashboard
├── models/                  # Pesos de los modelos YOLO (no versionados en
git)
├── tests/                   # Batería de tests (pytest)
├── Dockerfile.web           # Imagen de la API web
├── Dockerfile.worker        # Imagen del worker de análisis (con CUDA)
├── docker-compose.yml       # Orquestación local (modo monolítico)
└── .github/workflows/       # Pipelines CI/CD (ci.yml + deploy.yml)

51

Los pesos de los modelos YOLO (.pt) no se versionan en el repositorio por su tamaño

(>100  MB);  se  descargan  como  artefactos  del  pipeline  de  entrenamiento

documentado en el Anexo G y se montan como volumen externo en el worker.

La correspondencia entre ficheros y módulos sigue la misma división en 4 capas y 7

componentes funcionales definida en el diseño (véanse Sección 4.2 y Figura 5 para la

arquitectura lógica, y Sección 4.3 para la descomposición de componentes):

  Capa de Servicios: main.py expone los endpoints REST y WebSocket,

job_manager.py gestiona el ciclo de vida de los trabajos y schemas.py define los
modelos de validación Pydantic.

  Capa de Análisis (7 componentes del pipeline): batch_processor.py orquesta el

pipeline invocando en orden a tracker.py para el seguimiento ReID (componente
1), team_classifier.py para la clasificación CIELAB (componente 2),
possession.py para la estimación de posesión y pases (componente 3),
homography.py para la proyección al plano del campo (componente 4) y
tactical_engine.py para la generación de alertas (componente 5).
  Capa de Presentación: app.js mantiene la conexión WebSocket y actualiza el



dashboard al recibir cada MatchState parcial.
Infraestructura:
Se despliega mediante Dockerfile.web y Dockerfile.worker (con CUDA),
orquestados por docker-compose.yml, y los workflows ci.yml y deploy.yml
automatizan la integración continua y el despliegue en Cloud Run.

5.1.3 Implementación de la SPA y la comunicación en tiempo real

(WebSocket)

La interfaz de usuario de TacticAI es una Single Page Application (SPA) implementada

en  HTML5,  CSS3  y  JavaScript  vanilla  (sin  frameworks),  servida  como  contenido

estático directamente desde el contenedor de la API web. La decisión de no utilizar

un framework de frontend (React, Vue, Angular) responde a un criterio de simplicidad

de  despliegue:  la  SPA  no  requiere  proceso  de  compilación  ni  dependencias  de

Node.js, lo que reduce la complejidad de la imagen Docker y facilita la auditoría del

código por parte del cuerpo técnico. La SPA está estructurada como un dashboard de

dos vistas: (i) el formulario de carga, que permite subir un fichero de vídeo local (MP4,

AVI, MOV, MKV) mediante drag & drop o selección de fichero, o introducir una URL

de  stream  de  YouTube;  y  (ii)  el  panel  de  análisis,  que  muestra  en  tiempo  real  los

mapas de calor por equipo, las estadísticas de posesión y pases, y el feed de alertas

tácticas.

La comunicación entre el servidor y el dashboard se realiza mediante una conexión

52

WebSocket persistente, establecida en el momento en que el usuario inicia el análisis

y mantenida hasta que el worker termina de procesar el vídeo. Este protocolo se eligió

frente a las alternativas de polling HTTP o Server-Sent Events (SSE) por tres razones:

(i) permite comunicación bidireccional (el cliente puede enviar comandos de pausa o

cancelación al servidor sin abrir una nueva conexión HTTP); (ii) tiene menor overhead

que el polling al eliminar las cabeceras HTTP en cada mensaje; y (iii) está soportado

de  forma  nativa  en  todos  los  navegadores  modernos  sin  librerías  adicionales.  El

protocolo de mensajes es JSON: cada vez que el motor de análisis completa un micro-

lote, serializa el MatchState parcial y lo envía como un mensaje WebSocket al cliente;

la SPA recibe el mensaje, lo parsea y actualiza el DOM del dashboard sin recargar la

página,  proporcionando  la  sensación  de  actualización  en  tiempo  real.  La  latencia

media entre el fin del procesamiento de un micro-lote y la actualización visual del

dashboard  es  inferior  a  2  segundos  en  el  hardware  de  referencia.  Los  detalles  de

implementación del endpoint WebSocket (gestión de reconexiones, serialización del

MatchState, manejo de errores) se recogen en el Anexo I.

5.1.4 Capturas de la aplicación desplegada

Las  figuras  siguientes  muestran  la  interfaz  real  de  TacticAI  en  funcionamiento.  La

Figura 10 muestra la vista inicial de carga de vídeo; la Figura 11 muestra el dashboard

de análisis con los mapas de calor por equipo y el panel de Tactical Insights con las

alertas tácticas generadas.

Figura 10. Vista de carga de vídeo.

53

Figura 11. Dashboard de análisis en tiempo real: mapas de calor por equipo y panel Tactical Insights con alertas
tácticas generadas durante el análisis.

Este  capítulo  describe  la  implementación  del  sistema  TacticAI:  la  estructura  del

repositorio, los módulos principales y las decisiones técnicas de implementación más

relevantes.  Para  el  detalle  exhaustivo  de  cada  módulo  —algoritmos  completos,

fragmentos de código y configuración de hiperparámetros— se remite al Anexo  G

(módulos de visión), Anexo H (capa de servicios y despliegue) y Anexo I (resultados

de evaluación).

5.2 Pruebas automatizadas y CI

Las pruebas automatizadas son fundamentales en cualquier sistema de software con

múltiples  componentes

interactivos.  En  TacticAI,  el  riesgo  de  regresión  es

especialmente  alto  porque  los  cambios  en  el  pipeline  de  análisis  (por  ejemplo,  un

cambio  en  el  umbral  de  posesión  o  en  el  formato  de  serialización  del  estado

acumulado del partido) pueden afectar a todos los demás módulos que dependen de

esos datos. Sin un conjunto de tests automatizado, cada modificación requeriría una

verificación manual del sistema  completo, lo que es inviable a medida que el número

de componentes crece.

La  estrategia  de  testing  sigue  la  pirámide  de  tests  clásica:  muchos  tests  unitarios

rápidos (base de la pirámide), menos tests de integración más lentos (nivel medio), y

muy pocos tests de extremo a extremo  que requieren la infraestructura completa

(cima).

54

El proyecto mantiene seis ficheros de test en  tests/ :

• Tests de la capa de API: tests de los endpoints HTTP de la aplicación web

usando el cliente de test asíncrono del framework. Se verifica que los

endpoints devuelven los códigos de estado correctos, que el esquema JSON

de respuesta es conforme al modelo de datos, y que los errores (vídeo no

encontrado, trabajo en estado incorrecto) se manejan correctamente con los

códigos HTTP estándar.

• test_batch_processor: verificación de la secuencia de pasos del motor de

análisis con el detector mockeado (simulado mediante un objeto Python que

devuelve detecciones sintéticas predefinidas). Al sustituir el detector por un

simulacro, los tests pueden ejecutarse sin GPU y sin los pesos del modelo, lo

que hace los tests rápidos y reproducibles en cualquier entorno.

• test_match_state: tests de serialización/deserialización del estado

acumulativo del partido. Se verifica que un estado creado y serializado a

JSON puede recuperarse íntegramente, que los campos numéricos no

pierden precisión, y que los campos opcionales (heatmaps, alertas) se

manejan correctamente cuando están ausentes.

• test_possession_tracker: casos límite del módulo de posesión: qué ocurre

cuando no hay balón detectado en el frame, cuando dos jugadores están a la

misma distancia del balón, cuando la posesión cambia y se registra un pase.

Estos tests son especialmente valiosos porque el comportamiento del tracker

en casos límite es sutil y fácil de romper con cambios de umbral.

•  test_worker_integration: test de integración que simula el flujo completo:

creación de un job, encolado, procesamiento por el worker (con el detector

simulado y un vídeo sintético de test), y verificación del estado final. Este

test verifica que los componentes del sistema (almacenamiento, cola, base

de datos) están correctamente conectados entre sí.

• test_config_schema: validación del esquema de configuración del

sistema. Se verifica que los valores por defecto son

correctos, que las variables de entorno se cargan correctamente, y que los

valores inválidos (por ejemplo, un tamaño de lote negativo) son rechazados con

el error apropiado.

Los tests se ejecutan automáticamente mediante el workflow ci.yml de integración

55

continua  en  tres  versiones  de  Python  (3.11,  3.12,  3.13)  para  garantizar

compatibilidad.  El  workflow  falla  si  algún  test  no  pasa,  impidiendo  que  el  PR  sea

mergeado. La matriz de Python garantiza que no se introduzcan dependencias que

solo estén disponibles en una versión específica.

El workflow de despliegue continuo se activa solo en pushes a la rama principal (es

decir, después del merge del PR). Construye las imágenes Docker, las publica en el

registro de contenedores, y despliega en el entorno cloud. El despliegue es atómico:

si el build falla, la versión anterior permanece activa en producción.

Seguidamente se detallan en las tablas 13 y 14 los RF y RNF superados.

Pruebas funcionales

Tabla 14. Pruebas de requisitos funcionales.

RF

RF1

RF2

RF3

RF4

RF5

RF6

Descripción del requisito  Mecanismo de

Resultado

verificación

Carga de vídeo vía
navegador o ruta local

Detección YOLO en
GPU/CPU configurable

IDs persistentes a través
del vídeo

Asignación de equipo
por apariencia

Test de endpoint HTTP
de carga; formulario
web con fichero MP4 de
prueba

Test unitario con YOLO
mockeado; benchmark
en CPU y GPU con vídeo
de referencia (ver
§5.2.3)

Test de tracker con
detecciones sintéticas
con oclusiones
temporales

Inspección visual de
etiquetas sobre clips de
partido; test de
estabilidad temporal

✓ Superado

✓ Superado

✓ Superado

✓ Superado

Estimación de posesión
y conteo de pases

Tests unitarios de casos
límite (sin balón,
empate de distancia,
cambio de posesión)

✓ Superado

Homografía, zonas y
heatmaps opcionales

✓ Superado

Evaluación mAP@0.5
del detector de
keypoints (ver s.5.2.2);
inspección visual de
proyección

RF

RF7

RF8

RF9

56

Descripción del requisito  Mecanismo de

Resultado

verificación

Panel en tiempo casi
real vía WebSocket

Predicción heurística de
eventos y alertas

Trabajo asíncrono con
persistencia y cola

Prueba manual end-to-
end: vídeo de 90 min,
latencia por micro-lote <
2 s

Revisión manual de
alertas sobre clips con
jugadas conocidas

Test de integración:
flujo completo desde
trabajo encolado hasta
estado final con
componentes simulados

✓ Superado

✓ Superado (parcial)

✓ Superado

Pruebas no funcionales

Tabla 15. Pruebas de requisitos no funcionales.

RNF

RNF1

RNF2

RNF3

RNF4

Descripción del requisito  Mecanismo de verificación

Resultado

Rendimiento: micro-
batching para amortizar
inferencia GPU

Configurabilidad:
variables de entorno y
YAML

Portabilidad: fallback
CPU si no hay CUDA

Mantenibilidad: tests de
integración en CI

✓ Superado

✓ Superado

✓ Superado

✓ Superado

Benchmark sobre clips de
10 min con RTX 5070 Ti
Laptop; medición de fps
medios del pipeline y
latencia de micro-lote por
WebSocket (< 2 s en vídeo
de 90 min)

test_config_schema:
validación del esquema de
configuración; carga de
variables de entorno,
valores por defecto y
rechazo de valores
inválidos

test_batch_processor con
detector mockeado
ejecutado en entorno sin
GPU; matrix CI en tres
versiones de Python (3.11,
3.12, 3.13)

test_worker_integration:
flujo completo desde job
encolado hasta estado final
con componentes
simulados; workflow
ci.yml bloquea merge si
algún test falla

57

RNF

RNF5

RNF6

Descripción del requisito  Mecanismo de verificación

Resultado

Reproducibilidad:
Docker + dependencias
fijadas

Resiliencia: reanudación
de análisis
interrumpidos

✓ Superado

✓ Superado

Workflow CI construye y
despliega imágenes Docker
en cada push a rama
principal; dependencias con
versiones explícitas
verificadas en matrix de
tres versiones Python

test_match_state:
serialización/deserialización
del estado acumulativo del
partido; verificación de que
el estado se recupera
íntegramente tras
interrupción simulada

5.3 Métricas cuantitativas

Hardware de evaluación: NVIDIA GeForce RTX 5070 Ti Laptop GPU (12 GB VRAM GDDR7), CPU:

Intel Core i9-13ª generación, Python 3.13.9, PyTorch 2.9.1+cu128, CUDA 12.8, Ultralytics

8.3.234. Evaluación en batch_size=1 (equivalente al modo de producción del pipeline,

fotograma a fotograma).

5.3.1 Modelo de detección de elementos de juego

El  detector  principal  alcanza  un  mAP@0.5  de  0.893  sobre  el  conjunto  de  test,  un

resultado sólido para el dominio (los sistemas comerciales se mueven en 0.85–0.95).

La  clase  jugador  es  la  más  fiable  (mAP@0.5=0.971)  y  el  balón  el  mayor  desafío

(mAP@0.5=0.800), por su pequeño tamaño y sus frecuentes oclusiones. Para mitigar

en parte estas no-detecciones puntuales del modelo principal, el pipeline introduce

un algoritmo de seguimiento temporal (tracking). Este módulo enlaza las detecciones

frame a frame y estima la trayectoria del balón en los instantes en que el detector

físico lo pierde de vista. De este modo, se asegura la continuidad y persistencia de las

identidades de los elementos antes de realizar la asignación de equipos mediante el

algoritmo de clustering y de proyectar la información sobre la homografía obtenida a

través del segundo modelo YOLO (dedicado a la detección de keypoints del terreno

de juego). El desglose por clase y la tabla completa de métricas figuran en el Anexo I.

58

5.3.2 Modelo de keypoints del campo

El modelo de puntos clave del campo alcanza un mAP@0.5 de 0.956 sobre 15 tipos

de puntos, con una inferencia de solo ~10 ms por fotograma. Las esquinas del área

son los puntos más difíciles y los del círculo central los más fiables. El desglose por

tipo de punto se recoge en el Anexo I.

5.3.3 Análisis de rendimiento del pipeline completo

El pipeline completo procesa el vídeo a ~16 fps en el hardware de prueba , es decir,

en torno a 1,5× la duración real del vídeo; el micro-batching permite que el usuario

empiece  a  recibir  resultados  a  los  pocos  segundos.  Ninguna  configuración  de

hardware  de  consumo  probada  alcanza  los  25  fps  de  tiempo  real  estricto,  lo  que

confirma que el sistema es de análisis en diferido con actualización incremental, no

de tiempo real estricto. El desglose de tiempos por componente y los benchmarks por

hardware figuran en el Anexo I.

5.4 Gestión de riesgos y ética

Esta  sección  identifica  los  principales  riesgos  técnicos  del  proyecto  y  las  medidas

adoptadas para mitigarlos, y examina las implicaciones éticas del sistema: privacidad

de los datos de imagen, posibles sesgos del modelo y responsabilidad en el uso de las

recomendaciones generadas.

Tabla 16. Gestión de riesgos técnicos.

Riesgo

Prob.

Impacto  Mitigación en el proyecto

Pérdida del balón en

Alta

Medio

umbral de confianza reducido, detecciones máximas

detección

altas, sobremuestreo del balón en el conjunto de

entrenamiento

Identity switches en

Media  Medio

Re-ID con buffer de features,  max_lost_time

tracking

calibrado

Homografía inestable

Media

Bajo

Filtros anti-artefacto en líneas de gol, fallback sin

proyección

Coste GPU en nube

Baja

Alto

Micro-batching, optical flow off por defecto, workers

asíncronos

Imagen Docker grande

Baja

Bajo

Multi-stage build, pesos como volumen externo

Fugas de datos en

Baja

Alto

Auth en Cloud Run, buckets GCS privados, no

endpoints

secretos en código

59

Amenazas a la validez

Todo trabajo empírico está sujeto a posibles fuentes de error que conviene explicitar.

Esta sección describe las  principales amenazas  identificadas y  las medidas adoptadas

para mitigarlas.

Validez interna. La evaluación del rendimiento del pipeline se realizó sobre una muestra

limitada  de  secuencias  de  vídeo.  Factores  como  la  variación  en  las  condiciones  de

iluminación,  la  calidad  de  la  grabación  o  la  densidad  de  jugadores  pueden  sesgar  los

resultados hacia escenarios favorables. Para mitigarlo, se seleccionaron clips de partidos

reales con diversidad de condiciones (interior/exterior, cámaras fijas y en movimiento).

Validez externa. Los experimentos se ejecutaron en un único entorno hardware (RTX

5070 Ti Laptop). El rendimiento puede variar significativamente en CPUs convencionales

o en hardware embebido. Las métricas de latencia reportadas no deben generalizarse

sin validación en el entorno de despliegue objetivo.

Validez  de  constructo.  La  precisión  de  clasificación  de  equipos  y  la  tasa  de  identity

switches  del  tracker  son  proxies  imperfectos  de  la  utilidad  real  del  sistema  para  un

analista deportivo. No se realizó un estudio de usuario que evaluara la calidad percibida

de los análisis generados.

Amenazas de implementación. Al no disponer de un conjunto de datos etiquetado con

ground truth para todas las métricas (p. ej., posesión, eventos), parte de la validación es

cualitativa. Los tests automatizados cubren la corrección funcional, pero no la exactitud

estadística de las estimaciones en condiciones reales.

Ética  y  privacidad.  Los  vídeos  grabados  en  categorías  inferiores  pueden  contener

imágenes  de  menores;  su  tratamiento  requiere  cumplir  el  Reglamento  General  de

Protección  de  Datos  (RGPD/UE  2016/679)  y,  en  el  caso  de  menores,  contar  con  el

consentimiento  del  tutor  legal.  El  sistema  en  sí  no  realiza  identificación  personal  —

trabaja  con  tracks  anónimos  —  pero  el  operador  que  lo  despliega  asume  la

responsabilidad  sobre  los  datos  de  entrada.  Principios  adoptados  en  el  diseño:  (i)

minimización — no almacenar clips más tiempo del necesario; (ii) transparencia — las

estadísticas  son  estimaciones,  no  dictamen  arbitral;  (iii)  equidad  —  equipaciones

similares pueden degradar la clasificación; hay que comunicar las limitaciones al usuario.

60

CAPÍTULO 6

     Conclusiones y líneas futuras

6.1 Conclusiones

TacticAI ha sido desarrollado, documentado y validado como un sistema completo de

análisis táctico de fútbol sobre vídeo de retransmisión estándar.

6.1.1 Objetivos alcanzados

Objetivo 1 — Detección y tracking fiable de jugadores y balón. El modelo YOLO11m

fine-tuneado  alcanza  mAP@0.5=0.893  sobre  el  conjunto  de  test.  La  clase  player

(mAP=0.971)  y  referee  (mAP=0.944)  son  detectadas  con  alta  fiabilidad.  El  balón

(mAP=0.800) sigue  siendo el objeto más difícil, como es habitual en sistemas de este

tipo, pero los resultados son comparables a los obtenidos en trabajos similares de la

literatura.  El  tracker  ReID  mantiene

identidades  persistentes  con  suficiente

estabilidad para las métricas de posesión y pases.

Objetivo  2  —  Calibración  geométrica  del  campo.  El  modelo  de  keypoints  alcanza

mAP@0.5=0.956 para los 15 tipos de puntos de referencia del campo. La homografía

estimada permite proyectar posiciones de jugadores al plano del campo con precisión

métrica aceptable para visualizaciones tácticas (heatmaps). Las zonas de mayor error

son  los  planos  muy  cerrados  o  con  cámaras  de  ángulo  muy  oblicuo,  donde  pocos

keypoints son visibles simultáneamente.

Objetivo 3 — Métricas tácticas de utilidad para el cuerpo técnico. El sistema calcula

y presenta: (i) porcentaje de posesión por equipo, actualizado en baja latencia; (ii)

contador  de  pases  y  recuperaciones;  (iii)  mapas  de  calor  de  ocupación  del  campo

proyectados  en  coordenadas  métricas;  (iv)  alertas  del  motor  heurístico  sobre

condiciones  tácticas  de  riesgo  (pressing  alto,  oportunidad  de  contragolpe,  bloque

bajo). Estas métricas representan el núcleo del análisis post-partido que los analistas

realizaban manualmente antes del sistema.

Objetivo 4 — Interfaz web accesible. El dashboard web con gráficos interactivos y

actualizaciones en tiempo real vía WebSocket permite que el analista monitorice el

progreso  del  análisis  sin  conocimientos  técnicos.  La  interfaz  es  accesible  desde

cualquier navegador moderno, en local o en la nube.

61

Objetivo 5 — Arquitectura escalable y desplegable. La separación entre API y worker,

la containerización completa con Docker y el pipeline de CI/CD permiten desplegar el

sistema en un entorno cloud con un único comando.

6.1.2 Limitaciones identificadas

El proyecto presenta limitaciones técnicas que son relevantes para contextualizar los

resultados obtenidos:

  Velocidad de procesamiento: El sistema opera a ~16 FPS en el hardware de

prueba (RTX 5070 Ti Laptop), lo que equivale a ~1.5x la duración del vídeo. Esto

habilita la retroalimentación incremental y el análisis en diferido rápido, pero

impide operar en tiempo real estricto.

  Detección del balón: Presenta un recall del 73.1%, condicionado por falsos

negativos frente a oclusiones severas en jugadas de área, desenfoque por

movimiento (motion blur) a altas velocidades y planos excesivamente abiertos.

  Clasificación de equipos: El agrupamiento en el espacio CIELAB puede

desestabilizarse temporalmente si ambos equipos presentan equipaciones con

colores muy similares, ante cambios lumínicos bruscos entre micro-lotes o ante

equipos con equipaciones verdes.

  Homografía en planos cerrados: La estimación proyectiva resulta inviable en

maniobras de zoom muy cerradas, al no disponer del mínimo técnico de cuatro

keypoints visibles simultáneamente en el fotograma.

  Motor heurístico determinista: El sistema de eventos utiliza reglas predefinidas

sin aprendizaje automático. Aunque esto garantiza una total explicabilidad,

restringe la detección exclusivamente a los patrones tácticos anticipados

explícitamente por el diseñador.

6.2 Líneas futuras

  Núcleo analítico: Integración de algoritmos de seguimiento más robustos como

ByteTrack o BoT-SORT para reducir identity switches, implementación de

inferencia multiescala para mejorar el recall del balón en situaciones de

oclusión, fine-tuning del extractor ReID específicamente adaptado a secuencias

de fútbol y detección automatizada de formaciones y transiciones tácticas.

62

  Experiencia de usuario: Generación de informes automatizados post-partido

orientados al cuerpo técnico (exportación a PDF) , herramientas de

comparativa histórica de patrones tácticos entre diferentes partidos o equipos

rivales y habilitación de una interfaz para la corrección manual de asignaciones

erróneas por parte del analista.



Infraestructura y rendimiento: Despliegue de paneles de monitorización

MLOps (Grafana/Prometheus) para controlar el model drift en producción,

implementación de escalado horizontal en Cloud Run para el procesamiento

paralelo de múltiples partidos y exportación de los modelos YOLO a motores

como TensorRT para acelerar la inferencia en GPU y acercar el sistema al

tiempo real estricto.

63

BIBLIOGRAFÍA

     Bibliografía

1. Redmon, J., Divvala, S., Girshick, R., & Farhadi, A. (2016). You only look once: Unified, real-time

object detection. Proceedings of CVPR 2016, 779–788.

2. Jocher, G., Chaurasia, A., & Qiu, J. (2023). Ultralytics YOLO [Software].

https://github.com/ultralytics/ultralytics

3. Zhang, Y., Sun, P., Jiang, Y., Yu, W., Qu, Z., Han, W., & Wang, X. (2022). ByteTrack: Multi-object

tracking by associating every detection box. Proceedings of ECCV 2022, 1–21.

4. Luo, H., Gu, Y., Liao, X., Lai, S., & Jiang, W. (2019). Bag of tricks and a strong baseline for deep

person re-identification. Proceedings of CVPR Workshops 2019.

5. Bewley, A., Ge, Z., Ott, L., Ramos, F., & Upcroft, B. (2016). Simple online and realtime tracking.

Proceedings of ICIP 2016, 3464–3468.

6. Du, Y., Zhao, Z., Song, Y., Zhao, Y., Su, F., Gong, T., & Meng, H. (2023). StrongSORT: Make DeepSORT

great again. IEEE Transactions on Multimedia, 25, 8945–8958.

7. Hartley, R., & Zisserman, A. (2004). Multiple view geometry in computer vision (2.ª

ed.). Cambridge University Press.

8. Ramírez, S. (2023). FastAPI [Software]. Tiangolo. https://fastapi.tiangolo.com/

9. Google. (2024). Cloud Run documentation. Google Cloud. https://cloud.google.com/run/docs

10. OpenCV Team. (2024). OpenCV [Software]. https://opencv.org

11. Paszke, A., Gross, S., Massa, F., Lerer, A., Bradbury, J., Chanan, G., & Chintala, S. (2019).

PyTorch: An imperative style, high-performance deep learning library. Advances in Neural

Information Processing Systems, 32, 8026–8037.

12. Giancola, S., Amine, M., Dghly, T., & Ghanem, B. (2022). SoccerNet: A scalable dataset for

action spotting in soccer videos. Proceedings of CVPR Workshops 2022.

64

13. Cao, Z., Simon, T., Wei, S.-E., & Sheikh, Y. (2019). OpenPose: Realtime multi-person 2D pose

estimation using part affinity fields. IEEE Transactions on Pattern Analysis and Machine

Intelligence, 43(1), 172–186.

14. Rezatofighi, H., Tsoi, N., Gwak, J., Sadeghian, A., Reid, I., & Savarese, S. (2019). Generalized

intersection over union: A metric and a loss for bounding box regression. Proceedings of CVPR

2019, 658–666.

15. Wojke, N., Bewley, A., & Paulus, D. (2017). Simple online and realtime tracking with a deep

association metric. Proceedings of ICIP 2017, 3645–3649.

16. He, K., Zhang, X., Ren, S., & Sun, J. (2016). Deep residual learning for image recognition. Proceedings

of CVPR 2016, 770–778.

17. Ronneberger, O., Fischer, P., & Brox, T. (2015). U-Net: Convolutional networks for biomedical image

segmentation. Proceedings of MICCAI 2015, 234–241.

18. Szeliski, R. (2022). Computer vision: Algorithms and applications (2.ª ed.). Springer.

19. Abadi, M., Barham, P., Chen, J., Chen, Z., Davis, A., Dean, J., & Zheng, X. (2016). TensorFlow: A

system for large-scale machine learning. Proceedings of OSDI 2016, 265–283.

20. Peng, S., Liu, Y., Huang, Q., Zhou, X., & Bao, H. (2019). PVNet: Pixel-wise voting network for 6DoF

pose estimation. Proceedings of CVPR 2019, 4561–4570.

21. Cioppa, A., Giancola, S., Deliège, A., Kahl, K., Zhou, X., Somers, V., & Ghanem, B. (2022). SoccerNet-

Tracking: Multiple object tracking dataset and benchmark in soccer videos. Proceedings of CVPR

Workshops 2022.

22. IEEE. (1998). IEEE Std 830-1998: Recommended practice for software requirements specifications.

IEEE.

23. Sommerville, I. (2016). Ingeniería del software (10.ª ed.). Pearson.

24. ISO/IEC. (2011). ISO/IEC 25010:2011. Systems and software engineering — Systems and software

quality requirements and evaluation (SQuaRE). ISO/IEC.

25. Schwaber, K., & Sutherland, J. (2020). The Scrum guide. Scrum.org. https://scrumguides.org/

65

26. Docker Inc. (2024). Docker documentation. Docker. https://docs.docker.com

27. Staufer, L., & Huber, M. (2022). Sports analytics: Current state, challenges, and open problems. Data

Mining and Knowledge Discovery, 36, 1–36.

28. Parlamento Europeo y Consejo de la UE. (2016). Reglamento (UE) 2016/679 relativo a la protección

de las personas físicas en lo que respecta al tratamiento de datos personales. DOUE L 119, 1–88.

29. Merkel, D. (2014). Docker: Lightweight Linux containers for consistent development and deployment.

Linux Journal, 2014(239), 2.

30. Kalman, R. E. (1960). A new approach to linear filtering and prediction problems. Journal of Basic

Engineering, 82(1), 35–45. https://doi.org/10.1115/1.3662552

31. Kuhn, H. W. (1955). The Hungarian method for the assignment problem. Naval Research Logistics

Quarterly, 2(1–2), 83–97. https://doi.org/10.1002/nav.3800020109

32. Stats Perform. (2018). STATS Edge: AI-powered match preparation tool. Stats Perform.

https://www.statsperform.com/

33. Hudl. (2024). Wyscout platform: Football video and data analytics. Hudl.

https://www.hudl.com/en_gb/products/wyscout

34. Fischler, M. A., & Bolles, R. C. (1981). Random sample consensus: A paradigm for model fitting with

applications to image analysis and automated cartography. Communications of the ACM, 24(6),

381–395. https://doi.org/10.1145/358669.358692

35. Homayounfar, N., Fidler, S., & Urtasun, R. (2017). Sports field localization via deep structured

models. Proceedings of CVPR 2017, 5212–5220. https://doi.org/10.1109/CVPR.2017.553

36. ChyronHego. (2019). TRACAB Gen5 optical tracking system. ChyronHego.

https://chyronhego.com/sports-data/tracab/

37. Donadello, I., Dragoni, A. F., & Lenci, A. (2010). Unsupervised algorithms for segmentation and

clustering applied to soccer players classification. Proceedings of VISAPP 2010.

38. Mahfuz, S., Ahmed, F., & Al Rafi, M. (2023). Automatic team assignment and jersey number

recognition in football videos. Intelligent Automation & Soft Computing, 36(3).

66

https://doi.org/10.32604/iasc.2023.033224

39. Vats, K., Walters, P., Johannsen, A., & Bhatt, S. (2019). Associative embedding for game-agnostic

team discrimination. arXiv:1907.01058.

40. Cioppa, A., Deliège, A., & Giancola, S. (2020). A context-aware loss function for action spotting in

soccer videos. Proceedings of CVPR 2020. arXiv:1912.01326.

41. Hong, J., Fisher, M., Gharbi, M., & Durand, F. (2022). Spotting temporally precise, fine-grained

events in video. arXiv:2207.10213.

42. Lin, T.-Y., Maire, M., Belongie, S., Bourdev, L., Girshick, R., Hays, J., & Zitnick, C. L. (2014). Microsoft

COCO: Common objects in context. Proceedings of ECCV 2014, 740–755.

https://doi.org/10.1007/978-3-319-10602-1_48

67

USO DE IA

 Uso de herramientas de inteligencia artificial
generativa

Durante  el  desarrollo  de  este  TFG  se  han  utilizado  herramientas  de  inteligencia

artificial generativa de la siguiente forma:

Herramienta

Finalidad

Partes afectadas

Control de calidad

Claude

Asistencia en redacción de la

Capítulos 1–6,

Revisión crítica y reescritura

(Anthropic,

memoria, detección de

anexos

sustancial; verificación de

versión Claude

errores tipográficos y

exactitud técnica frente al

Sonnet 4.6)

propuestas de estructura

código fuente

GitHub Copilot

Sugerencias de código en IDE

Fragmentos de

Revisión y modificación de

código en

modules/

todas las sugerencias

aceptadas; tests

automatizados

El/la estudiante es el/la único/a responsable del contenido íntegro del TFG. Durante

la  defensa  oral  será  capaz  de  explicar  y  justificar  cada  afirmación,  dato,  figura,

fragmento de código, procedimiento y decisión metodológica.

68

ANEXO  A

     Clases YOLO del sistema

Clases definidas en  soccernet.yaml :

ID

Clase

Notas

0

1

2

3

4

player

ball

Jugador de campo genérico

Balón

referee

Árbitro — excluido de estadísticas de posesión

goalkeeper

Portero — clase dedicada para reglas específicas

player_team_left

Experimental: jugador con lateralización de equipo en etiqueta

69

ANEXO  B

     Comandos de entrenamiento

# Modelo principal de detección

yolo detect train \

data=soccernet.yaml \

model=yolo11m.pt \

epochs=100 imgsz=640 batch=16 \

device=0 project=runs name=detect_football_v1

# Modelo de keypoints del campo

yolo detect train \

data=field_keypoints.yaml \

model=yolo11m.pt \

epochs=100 imgsz=960 batch=8 \

device=0 patience=25 cos_lr=True

70

ANEXO  C

     Arranque local

# Modo legacy (app.py + WebSocket)

python -m venv venv

source venv/bin/activate

pip install -r requirements.txt

python app.py

# Navegador: http://localhost:8001

# Modo dual API (app_service)

export DATABASE_URL=sqlite:///./runtime_data/jobs.db

./scripts/db_manage.sh init-local

./scripts/run_local.sh

# Navegador: http://localhost:8000

71

ANEXO D

     Bitácora de ingeniería (iteraciones)

Iteración  Hito

Lección principal

1

2

3

4

5

6

7

8

9

Primera inferencia YOLO

Modelo genérico confunde público con jugadores; fine-

sobre vídeo de fútbol

tuning es imprescindible

Separación

Clases dedicadas simplifican enormemente las reglas

semántica  player  /

posteriores

goalkeeper / referee

Tracking estable con Re-ID

Los identity switches en jugadas de área revelan los límites del

tracker y la importancia de max_lost_time

Posesión determinista con

Sin histéresis temporal la posesión oscila por ruido; una

histéresis

ventana de 3-5 frames estabiliza la señal

Homografía y heatmaps

La calibración proyectiva añade valor pero introduce

artefactos; los filtros de máscara mitigan acumulaciones

falsas en líneas de gol

Motor de predicción +

Separar cálculo de probabilidades (YAML/Python) de narrativa

alertas

(LLM) es clave para trazabilidad y defensa oral

Interfaz web con

El micro-batching asíncrono es fundamental para no

WebSockets

bloquear el hilo de petición HTTP

Arquitectura desacoplada:

La abstracción de providers (storage, queue, db)

API + worker

permite migrar de local a cloud sin modificar el

núcleo analítico

DevOps: Docker + GitHub

Los workflows automatizados detectan regresiones antes de

Actions + Cloud Build

que lleguen a producción; el multi-stage build reduce el

tamaño de imagen ≈40%

72

ANEXO E

     Glosario de términos

Término

Definición

Bounding box

Rectángulo axis-aligned que encierra un objeto detectado en imagen

NMS

Non-Maximum Suppression: elimina detecciones redundantes solapadas

manteniendo la de mayor confianza

Re-ID

Re-identificación: reconocer que dos apariciones en distintos fotogramas

corresponden al mismo jugador

Homografía

Transformación proyectiva plano-plano 3×3 que relaciona la imagen de cámara

con el modelo 2D del campo

Heatmap

Mapa de densidad acumulada de presencias de jugadores proyectadas al campo

Micro-batching

Procesar fotogramas en grupos (p. ej. 3 s de vídeo) para amortizar la

inferencia en GPU

Cooldown

Tiempo mínimo entre emisiones del mismo tipo de alerta para evitar duplicados

ROI

Región de interés: recorte de imagen centrado en la detección, usado para

color o Re-ID

mAP

MOTA

Mean Average Precision: métrica estándar de evaluación de detectores de objetos

Multiple Object Tracking Accuracy: combina FP, FN y identity switches en un

único valor

IDF1

Identity F1: métrica de tracking que enfatiza la consistencia de las

identidades a lo largo del tiempo

Sigmoid

Función σ(x) = 1/(1+e⁻ˣ) que mapea una puntuación lineal a probabilidad en [0,1]

Estado del partido
(MatchState)

Objeto serializable que acumula el estado completo del análisis de un partido

entre batches

BackgroundTask  Mecanismo del servidor web que despacha una tarea pesada fuera del hilo de la

petición HTTP

73

                ANEXO F

    Conjuntos de datos y proceso de entrenamiento

El  dataset  de  entrenamiento  se  construyó  combinando  dos  fuentes:  imágenes  del

dataset  SoccerNet  (partidos  de  fútbol  europeo  con  licencia  de  investigación)  y

grabaciones  propias capturadas con distintas cámaras y condiciones de iluminación.

El proceso de curación siguió las siguientes etapas:

1. Selección  y  muestreo  de  vídeo.  Se  seleccionaron  secuencias  con

variedad  de  encuadre  (plano  amplio,  plano  medio  y  seguimiento

cerrado), diversidad de estadios  (interior,  exterior,  con  y  sin  público),

condiciones  de  luz  (diurno,  nocturno  con  iluminación  artificial)  y

condiciones  meteorológicas  (día  soleado,  nublado,  lluvia  leve).  La

variedad es imprescindible para que el modelo generalice.

2. Muestreo  de  fotogramas.  Se  utilizó  una  combinación  de  muestreo

uniforme (1 de cada k fotogramas para evitar redundancia temporal) y

muestreo  dirigido  por  movimiento  (diferencia  absoluta  media  entre

frames  consecutivos,  para  capturar  más

instancias  en

jugadas

dinámicas) y sobremuestreo de fotogramas con balón (para compensar

el desequilibrio de clases: hay ~83 500 instancias de player frente a ~7

500 de ball).

3. Etiquetado  manual.  Cada  objeto  recibe  un  rectángulo  axis-aligned

siguiendo  lineamientos  estrictos:  (i)  el  bounding  box  del  jugador

incluye  cabeza  y  botas,  sin  excluir  partes  fuera  del  campo;  (ii)  el

portero recibe la clase  goalkeeper independientemente del color

de su equipación; (iii) el árbitro recibe la clase referee para que el

sistema pueda excluirlo de las estadísticas de posesión; (iv) el balón se

etiqueta con un bounding box ceñido al perímetro visible, incluyendo

solo el área realmente visible cuando está parcialmente oculto.

4. Revisión cruzada de calidad (QA). Un segundo paso revisó el 15% del

conjunto de forma aleatoria, corrigiendo cajas mal alineadas, clases

incorrectas (árbitros etiquetados como jugadores) y oclusiones mal

gestionadas.  Este  paso  redujo  significativamente  la  tasa  de  errores

sistemáticos.

74

El dataset final contiene 9 621 imágenes con 104 516 instancias distribuidas en las

cuatro clases. La distribución de clases es desbalanceada por naturaleza del dominio:

la clase player domina con 83 547 instancias, mientras que goalkeeper tiene solo 5

924.  Para  mitigar  este  desequilibrio,  Ultralytics  aplica  augmentaciones  de  mosaico

(combina  4  imágenes  en  una)  y  HSV-jitter  que  aumentan  la  variedad  sintética  del

dataset.

Dataset del modelo de keypoints del campo

El modelo de keypoints detecta 15 tipos de puntos de referencia del terreno de juego,

necesarios  para  estimar  la  homografía  imagen-campo.  Los  keypoints  incluyen:

esquinas  del  campo  y  del  área,  intersecciones  de  la  línea  central  con  las  bandas,

puntos  del  arco  del  área,  intersecciones  de  la  línea  media  con  los  semicírculos,  y

esquinas de las áreas pequeñas. Con estos 15 tipos, se puede recuperar suficiente

información  geométrica  para  estimar  la  homografía  mediante  RANSAC,  incluso

cuando no todos los keypoints son visibles en cada fotograma.

El dataset contiene 498 imágenes con 4 349 instancias de keypoints, un volumen más

modesto  pero  suficiente  dado  que  la  geometría  del  terreno  es  consistente  entre

partidos.  El  modelo  alcanza  mAP@0.5=0.956  (Tabla  22),  resultado  especialmente

notable  dada  la  dificultad  de  los  keypoints  de  esquinas  del  arco  del  área  (corner:

mAP@0.5=0.894) que son los más sensibles a la perspectiva y la distancia a la cámara.

Proceso de entrenamiento

Ambos modelos se entrenaron con la CLI de Ultralytics (yolo detect train) sobre

el  hardware  descrito  en  la  Sección  5.2.  Los  hiperparámetros  principales  se

documentan en la Tabla 17. Los puntos más relevantes son:

• Transfer  learning  desde  COCO:  los  pesos  yolo11m.pt  pre-entrenados  en

COCO  proporcionan  un  punto  de  partida  con  características  visuales

generales  ya  aprendidas.  El  fine-tuning  sobre  el  dataset  de  fútbol  ajusta

estas  características  al  dominio  específico,  logrando  convergencia  mucho

más rápida que el entrenamiento desde cero (scratch).

• Augmentación  de  datos:  la  configuración  por  defecto  de  Ultralytics  aplica

Mosaic (combina 4 imágenes), MixUp (mezcla de dos imágenes con factor α),

flip horizontal, y jitter en HSV (matiz ±1.5%, saturación ±70%, valor ±40%). Estas

75

augmentaciones  son  especialmente  importantes  para  el  balón,  que  tiene

apariencia muy variable según la iluminación y el ángulo.

• Early  stopping  con  patience=25  :  el  entrenamiento  se  detiene

automáticamente  si  la  métrica  de  validación  no  mejora  en  25  épocas

consecutivas,  evitando  el  sobreajuste  y  reduciendo  el  tiempo  de

entrenamiento cuando el modelo ya ha convergido.

• Cosine LR annealing: la tasa de aprendizaje sigue una curva coseno desde el

valor  inicial  hasta  cercano  a  cero,  lo que  facilita  la  convergencia  fina  en  las

últimas épocas.

Tabla 17. Hiperparámetros de entrenamiento del detector principal.

Parámetro

Valor

Justificación

model

epochs

imgsz

batch

conf (inferencia)

iou (NMS)

patience

augment

yolo11m.pt

Balance calidad/velocidad en inferencia

100

640

16

0.30

0.45

25

True

Suficiente convergencia con early stopping

Trade-off resolución/FPS para GPU de gama media

Cabe en 6 GB VRAM; se reduce a 8 en keypoints

Balance recall/precision; el balón necesita umbral bajo

Evita duplicados en jugadores cercanos

Para overfitting; activa con cos_lr=True

Mosaic, flip, HSV shift para robustez fotométrica

Guía del dataset y entrenamiento

Fase  A  —  Recogida  de  vídeo.  Se  seleccionan  grabaciones  con  variedad  de

condiciones: encuadre amplio vs. cerrado, día vs. noche artificial, lluvia, fondos con

público y sin público.

Fase B — Muestreo de fotogramas. Muestreo uniforme (1 de cada k fotogramas),

dirigido  por  movimiento  (diferencia  absoluta  media)  y  balance  de  clases

(sobremuestreo de fotogramas con balón).

Fase C — Etiquetado. Cada objeto recibe un rectángulo axis-aligned. Lineamientos:

76

jugador incluye cabeza y botas; portero con clase distinta; árbitro para excluirlo de

estadísticas; balón ceñido al perímetro visible.

Fase D — Revisión cruzada. Un segundo paso de QA sobre el 10–20% del conjunto

reduce errores sistemáticos.

Fase  E  —  Entrenamiento  (Ultralytics).  El  entrenamiento  se  lanza  con  la  CLI  yolo

detect  train  y  data=  soccernet.yaml.  Los  artefactos  se  guardan  en

runs/detect/<name>:  las  curvas  results.png,  la  matriz  confusion_matrix.png  y  los

pesos best.pt.

77

ANEXO G

     Detalle técnico de los módulos de visión

Puntos de entrada del pipeline

El pipeline de análisis es el núcleo del sistema. Se activa desde tres puntos de entrada

posibles:

la

función

run_match_analysis()  de  app.py

(modo  monolítico),

LocalPipelineRunner (vía WebSocket legacy) y el worker de análisis (modo cloud).

Ingesta de vídeo: parámetros de micro-lote

El módulo de ingesta implementa el patrón de diseño Iterator sobre fuentes de vídeo

heterogéneas.  La

interfaz  pública  expone  un  único  método  que  devuelve

iterativamente micro-lotes de fotogramas como arrays NumPy de forma (N, H, W, 3)

en el espacio de color BGR (convención OpenCV).

El  parámetro  batch_duration_seconds  controla  cuántos  segundos  de  vídeo  se

acumulan por lote. Con 25 fps y batch_duration_seconds=3, cada lote contiene 75

fotogramas. Este valor es un compromiso entre:

• Latencia de actualización: valores pequeños (1–2 s) producen actualizaciones

más  frecuentes  en  el  dashboard,  pero  aumentan  el  overhead  relativo  de

preparación del lote.

• Eficiencia  GPU:  el  procesamiento  por  lotes  (batched  inference)  amortiza  el

coste de arranque de la inferencia YOLO sobre GPU. Con lotes muy pequeños,

la GPU está mayoritariamente ociosa esperando datos.

• Consistencia temporal del clasificador de equipos: el módulo de clasificación

necesita  acumular suficientes observaciones por track para que el clustering

sea estable. Con lotes de menos de 1 segundo (25 frames), los equipos pueden

no haberse observado lo suficiente para convergir.

Internamente, el módulo usa OpenCV (cv2.VideoCapture) para descodificar el vídeo

en CPU. La descodificación es el cuello  de botella principal en CPU; para vídeo HD

(1920×1080)  a  25  fps,  OpenCV  emplea  del  orden  de  5–10  ms  por  fotograma  en

hardware moderno. El redimensionado a 640×640 se realiza dentro del  pipeline de

78

YOLO, no en la ingesta.

Detección de objetos: arquitectura YOLO11

YOLO11  (You  Only  Look  Once,  versión  11)  es  un  detector  de  objetos  de  una  sola

pasada:  la  imagen  de  entrada  se  procesa  una  única  vez  por  la  red  neuronal  y  se

obtiene  directamente el  conjunto  de cajas detectadas con sus clases y confianzas.

Esto  contrasta  con  los  detectores  de  dos  etapas  (Faster  R-CNN)  que  primero

proponen regiones candidatas y después las clasifican, lo que los hace más precisos,

pero mucho más lentos.

La arquitectura YOLO11 se basa en tres componentes:

1. Backbone: extractor de características convolucional (basado en CSP-DarkNet

mejorado) que produce mapas de características a distintas escalas. YOLO11m

tiene 125 capas y 20M parámetros.

2. Neck  (FPN  +  PAN):  red  de  pirámide  de  características  (Feature  Pyramid

Network)  que  combina  información  de  distintas  escalas  del  backbone  para

detectar  objetos  de  distintos  tamaños.  El  cuello  PAN  (Path  Aggregation

Network)  añade  un  camino  bottom-up  que  mejora  la  propagación  de

información  de capas bajas (detalles  finos,  importante  para  el  balón  que  es

pequeño) hacia capas altas.

3. Head: módulo de predicción que, para cada celda de la cuadrícula de salida,

predice directamente las coordenadas de las cajas y las probabilidades de clase

sin  anclas  fijas  (anchor-free  en  YOLO11).  Esto  simplifica  la  configuración  y

mejora la generalización.

En  el  pipeline,  YOLO  se  invoca  con  imgsz=640)  .  El  umbral  de  confianza  es

deliberadamente bajo para maximizar el recall del balón (que es la detección más difícil),

a  costa  de  aceptar  algunos  falsos  positivos  que  el  tracker  filtrará  temporalmente.  El

umbral de IoU para NMS evita duplicados cuando dos jugadores aparecen muy próximos.

Seguimiento multi-objeto (ReID)

El módulo de re-identificación (ReID) resuelve el problema de tracking multi-objeto:

dada una secuencia de detecciones frame a frame, asignar un ID permanente a cada

instancia  detectada,  manteniéndolo

incluso  cuando  el  objeto  desaparece

79

brevemente del cuadro y vuelve a aparecer.

El algoritmo funciona en tres pasos por cada fotograma:

1. Extracción  de  embeddings  de  apariencia.  Para  cada  bounding  box

detectado, se recorta la región de imagen correspondiente y se pasa por

un  extractor  de  características  ligero  (CNN  de  extracción  de  features,

típicamente basado en ResNet18 o MobileNet) que produce un vector de

embedding  de  128–512  dimensiones.  Este  vector  captura  la  apariencia

visual del objeto: color de equipación, número en la camiseta, proporción

del cuerpo.

2. Asociación mediante distancia coseno + IoU. Los embeddings de las nuevas

detecciones se comparan con los embeddings guardados en el buffer de tracks

activos. La métrica de asignación combina distancia coseno entre embeddings

(para apariencia) y la IoU entre cajas predichas por el modelo de movimiento

(filtro de Kalman) y las cajas detectadas. Esta combinación es más robusta que

usar solo posición (útil cuando dos jugadores se cruzan) o solo apariencia (útil

cuando la cámara hace zoom o corte).

3. Resolución  de  asignaciones  con  el  algoritmo  húngaro.  La  matriz  de

costes  (distancias  combinadas)  se  resuelve  con  el  algoritmo  de

asignación  húngara  (también  llamado  método  de  Munkres),  que

encuentra  la  asignación  de  coste  mínimo.  Las  detecciones  sin  track

asignado  inician  nuevos  tracks;  los  tracks  sin  detección  asignada  se

marcan  como  lost  y  se  mantienen  en  el  buffer  durante  max_lost

fotogramas por si el objeto reaparece.

El parámetro max_lost es crítico: demasiado corto provoca que los tracks se pierdan

en oclusiones cortas y se reasignen con  un ID nuevo cuando el jugador reaparece

(identity  switch);  demasiado  largo  hace  que  el  buffer  crezca  indefinidamente  con

tracks  fantasma  que  contaminan  el  clustering  de  equipos.  El  valor  calibrado  en  el

proyecto es de 15–25 fotogramas (0.6–1 segundo a 25 fps).

Clasificación de equipos

Una vez que cada jugador tiene un track ID persistente, el módulo de clasificación de

equipos le asigna uno de los dos equipos (equipo A / equipo B, luego mapeados a

80

local/visitante).  Este  es  uno  de  los  problemas  más  sutiles  del  sistema,  porque  las

condiciones de iluminación hacen que el mismo  color de equipación se perciba de

forma muy distinta entre estadios y horas del día.

La cadena de procesamiento es la siguiente:

1. Extracción de ROI del torso. En lugar de usar todo el bounding box del jugador

(que incluye fondo, campo, otras personas), se recorta solo la región del torso

(aproximadamente  el  30–60%  central  de  la  caja  en  altura,  20–80%  en

anchura). El torso es la región más informativa para el color de la equipación y

la menos ruidosa.

2. Máscara anti-verde. El césped del campo domina el fondo de muchas ROIs.

Se aplica una máscara HSV que elimina los píxeles con tonalidad verde (H ≈

60–120°),

reduciendo el ruido del fondo y mejorando la representatividad de la muestra de color.
3. Máscara anti-dorsal. Los números y letras del dorsal de la camiseta suelen ser

blancos o negros y pueden confundir el  clustering. Se aplica un  detector de

bordes  (Canny)  seguido  de  una  dilatación  para  identificar  y  enmascarar  las

regiones con alta densidad de bordes, que corresponden a texto o números.

4. Extracción de features en el espacio CIELAB. Los píxeles no enmascarados se

convierten al espacio de color CIELAB (L*a*b*). Se usan solo los canales a*

(verde-rojo) y b* (azul-amarillo), omitiendo L* (luminosidad). La razón es que

el espacio LAB está diseñado para ser perceptualmente uniforme y separar la

crominancia de la luminancia: dos muestras del mismo color bajo diferente

iluminación tendrán valores a*, b* similares aunque L* cambie.

5. KMeans k=2 con acumulación temporal. Se acumulan los vectores (a*, b*) de

todos los fotogramas del batch (no solo uno) y se aplica KMeans con k=2. Al

acumular sobre múltiples fotogramas se reduce la varianza del  clustering. El

resultado asigna cada track a uno de los dos centroides (equipo A o equipo B).

6. Votación temporal (histéresis). La asignación de equipo de un track no cambia

en cada frame: se mantiene una historia de las últimas N asignaciones y la clase

mayoritaria es la que prevalece. Esto evita el flickering (cambios espurios de

equipo  frame  a  frame)  que  ocurre  cuando  el  tracker  pierde  al  jugador

momentáneamente  y

lo  reencuentra  con  un  embedding

ligeramente

diferente.

81

Las  principales  limitaciones  del  sistema  de  clasificación  son:  (i)  si  los  dos  equipos

visten equipaciones de colores muy similares (dos equipos con camisetas blancas, por

ejemplo),  el  clustering  no  puede  separarlos  correctamente;  (ii)  el  portero  viste  un

color diferente que puede confundirse con el equipo contrario —se trata con la clase

goalkeeper por separado—; (iii) los cambios de equipación a mitad del partido (lesión,

segunda equipación) no se manejan actualmente.

Estimación de posesión y detección de pases

El  módulo  de  estimación  de  posesión  implementa  un  modelo  determinista

simplificado  de  posesión  del  balón.  No  se  usa  detección  de  contacto  físico  (que

requeriría  alta  resolución  o  sensores  de  velocidad  del  balón),  sino  un  criterio  de

proximidad con histéresis temporal:

1. Cálculo  de  distancias  al  balón.  En  cada  fotograma  donde  el  balón  es

detectado, se calcula la distancia euclidiana en píxeles entre el centro del balón

y el centro inferior de cada bounding box de jugador (pie, que es la zona más

relevante para el contacto).

2. Selección del jugador más cercano. El jugador con menor distancia al balón

(por  debajo de  un umbral  possession_distance_px , configurable) se

considera en posesión.

3. Histéresis de posesión. La posesión no cambia en cuanto otro jugador esté 1

píxel más cerca: se requiere que el nuevo jugador esté más cerca que el actual

durante  al  menos  possession_frames_threshold  fotogramas  consecutivos.

Esta histéresis es esencial para estabilizar la posesión en disputas, donde el

balón oscila entre dos jugadores a muy corta distancia.

4. Detección  de  pases.  Un  pase  se  registra  cuando  la  posesión  cambia  de  un

jugador  a  otro  del  mismo  equipo.  Cuando  la  posesión  cambia  al  equipo

contrario, se registra una recuperación (tackle o pérdida). La cadencia de pases

por  equipo  se  acumula  en  el  estado  del  partido  para  su  visualización  en  el

dashboard.

Las limitaciones principales de este modelo son: (i) cuando el balón no es detectado

(oclusión, imagen borrosa por movimiento), no se puede actualizar la posesión y el

último estado se mantiene congelado; (ii) en situaciones de lucha por el balón con

82

múltiples  jugadores  muy  próximos,  el  modelo  asigna  la  posesión  al  jugador

geométricamente más cercano, que puede no ser el que realmente lo controla; (iii)

los tiros y despejes (balón en el aire) pueden asignarse erróneamente a un jugador

que esté debajo de la trayectoria del balón.

Proyección geométrica (homografía)

La  homografía  imagen-campo  permite  transformar  coordenadas  en  píxeles  de  la

imagen de la cámara en coordenadas métricas del terreno de juego (metros desde la

esquina inferior izquierda, por ejemplo). Esto habilita las métricas más valiosas desde

el  punto  de  vista  táctico:  distancias  recorridas,  profundidad  de  línea  defensiva,

amplitud de ataque, distancia entre líneas.

Fundamento matemático. Una homografía plana es una transformación proyectiva

que relaciona dos planos. En nuestro caso, el plano imagen de la cámara y el plano

del terreno de juego (que se asume plano, lo cual es una buena aproximación para un

campo de fútbol estándar). Se representa como una matriz H de 3×3 con 8 grados de

libertad  (la  escala  es  arbitraria).  Para  estimar  H  se  necesitan  al  menos  4

correspondencias punto-a-punto entre los dos planos (aunque en la práctica se usan

muchas más para RANSAC):

x_campo = H · x_imagen

(en coordenadas homogéneas)

[X, Y, W]^T = H · [u, v, 1]^T

coordenadas métricas: (X/W, Y/W)

Proceso de estimación. El modelo de detección de puntos clave del campo detecta los
15 tipos de puntos de referencia en cada fotograma. Cada tipo de keypoint tiene una
posición conocida en las coordenadas del campo estándar (según el reglamento de la
FIFA: campo de 105 m × 68 m). Así se obtienen pares de correspondencias (u, v) →

RANSAC itera seleccionando aleatoriamente grupos de 4 correspondencias, estima la

homografía  tentativa,  cuenta  los  inliers  (correspondencias  que  se  ajustan  bien  al

modelo) y conserva la homografía con más inliers.

Filtros  anti-artefacto.  La  homografía  puede  producir  artefactos  cuando  la  cámara

tiene un ángulo muy oblicuo o cuando pocos keypoints son detectados: los heatmaps

se acumulan fuera del campo real, en coordenadas negativas o por encima de 105×68

m. Para evitarlo, se aplican filtros: (i)  umbral mínimo de  inliers en RANSAC (si hay

menos de N inliers, la homografía se descarta para ese frame); (ii) comprobación de

83

que la transformación de  las esquinas del campo da un polígono convexo dentro de

los límites esperados; (iii) recorte de heatmaps a la región [0, 105] × [0, 68].

Impacto  sobre  el  rendimiento.  La  detección  de  keypoints  añade  ~10  ms  por

fotograma (inferencia del segundo modelo YOLO). El cálculo de  la homografía con

OpenCV  es  negligible  (submilisegundo).  La  proyección  de  las  posiciones  de  los

jugadores también es instantánea. El módulo es opcional: si se desactiva, el sistema

sigue funcionando pero sin coordenadas métricas ni heatmaps proyectados al campo.

Motor de predicción táctica de eventos

El motor de predicción de eventos tácticos implementa un sistema de alertas tácticas

configurable. Su filosofía de diseño es fundamental: las probabilidades las calcula el

código Python, no el modelo de lenguaje. Si se usa un LLM externo para generar texto,

el modelo de lenguaje solo reformula en español natural una alerta ya cuantificada;

nunca decide si un evento es probable o no.

La configuración del motor se almacena en un fichero de configuración, que define

para  cada  tipo  de  evento  (p.  ej.,  pressing_risk,  counterattack_opportunity,

low_block_defense):

• Señales  (signals):  lista  de  indicadores  tácticos  con  su  peso.  Por  ejemplo:

posesión_equipo_A > 70% en los últimos 30s (peso 0.4), número de jugadores

equipo_B en campo propio > 8 (peso 0.3), tiempo_sin_pases_equipo_B > 15s

(peso 0.3).

• Función  de puntuación: suma  ponderada de  señales  normalizadas,  pasada

por una función sigmoide σ(x) = 1/(1+e⁻ˣ) para obtener una probabilidad en

[0, 1].

• Umbral de activación: si la puntuación supera un umbral configurable (p. ej.,

0.65), se genera una alerta.

• Cooldown:  tiempo  mínimo  entre  dos  alertas  del  mismo  tipo  (p.  ej.,  30

segundos).  Evita  que  una  alerta  se  emita  repetidamente  en  cada  batch

mientras la condición táctica persiste.

• Texto  de  alerta:  plantilla  de  texto  que  se  muestra  en  el  dashboard,  con

posibilidad de enriquecimiento por LLM.

84

Esta arquitectura es altamente explicable: dado un conjunto de alertas generadas, se

puede trazar exactamente qué señales contribuyeron a cada una y con qué peso.

TeamClassifierV2 — cadena de procesamiento

El clasificador de equipos sigue: (1) ROI de torso; (2) anti-green (máscara HSV); (3)

anti-dorsal  (filtros  de  borde  +  dilatación);  (4)  features  LAB  a*,  b*  para  robustez

fotométrica; (5) KMeans k=2 sobre acumulados por track; (6) votación temporal para

evitar cambios por flicker.

85

Catálogo de módulos de implementación

Tabla 18. Catálogo de módulos principales del sistema.

Módulo

Responsabilidad

Clave para

batch_processor

Orquestador  por  micro-lote  (pasos  1–12  del

RF2–

diagrama)

RF8,

RNF1

match_analyzer

Bucle  principal  de

análisis;

gestión  de

RF7, RNF1

video_sources

match_state

configuración y callback WebSocket

Abstracción de fuente  de vídeo,  producción

RF1, RNF3

de micro-lotes

Estado acumulativo del partido con persistencia
en fichero o caché distribuida

RF9, RNF6

reid_tracker

Matching  de  embeddings  de  apariencia  +

RF3

buffer de tracks

team_classifier_v2

Clustering  LAB  k=2  con  anti-green/dorsal  +

RF4

histéresis temporal

possession_tracker_v2

Posesión  determinista  +  conteo  de  pases

RF5

con histéresis

field_keypoints_yolo

Detección  de  keypoints  del  terreno

RF6

para homografía

field_heatmap_system

Proyección  +  acumulación  de  heatmaps

RF6

por equipo

event_prediction_engine

Motor  heurístico  YAML:  pesos,  umbrales,

RF8

cooldowns

match_alert_system

Emisión  de  alertas  tácticas  con  deduplicación

RF8

temporal

prediction_anthropic

Wrapper  LLM  (Anthropic)  para  narrativa  en

RF8

lenguaje natural

(opcional)

86

          ANEXO H

     Capa de servicios y despliegue (detalle)

WebSocket y streaming incremental

El protocolo WebSocket permite comunicación bidireccional y full-duplex sobre una

conexión  TCP  persistente.  A  diferencia  del  modelo  request-response  de  HTTP,  el

servidor puede enviar datos al cliente en cualquier momento sin que el cliente los

solicite explícitamente. Esta característica es exactamente lo que necesita TacticAI: el

servidor analiza el vídeo en background y envía actualizaciones al dashboard cada vez

que completa un micro-lote.

Las alternativas consideradas fueron:

• HTTP polling: el cliente pregunta al servidor «¿hay nuevos datos?» cada N

segundos. Simple de implementar pero ineficiente (muchas peticiones vacías)

y con latencia mínima de N segundos.

• Server-Sent Events (SSE): el servidor envía un stream unidireccional de

eventos al cliente. Más sencillo que WebSocket (solo texto, solo

servidor→cliente) y suficiente para el modo seguimiento de trabajos.

• WebSocket: elegido para el modo monolítico por su soporte nativo en

FastAPI  y  la  bidireccionalidad  (el  cliente  puede  cancelar  el  análisis

enviando un mensaje de control al servidor).

En

la  implementación  con  FastAPI,  el  endpoint  WebSocket  se  declara  con

@app.websocket("/ws/{job_id}"). El análisis se lanza como una corrutina asíncrona

(BackgroundTask)  que  corre  en  el  event  loop  de  asyncio.  Los  resultados  de  cada

batch se serializan a JSON y se envían con await websocket.send_json(chunk_data).

a JSON y se envían con await websocket.send_json(chunk_data). La serialización usa

el método to_dict() del objeto ChunkResult, que excluye los arrays NumPy pesados

(heatmaps) y envía solo los datos estadísticos ligeros.

Patrón dual API: servicio web + proceso de análisis desacoplado

El modo dual API desacopla la interfaz HTTP (que debe responder en milisegundos)

del análisis de vídeo (que puede tardar minutos). El patrón es similar a los sistemas

de colas de tareas asíncronas (Celery, RQ) pero implementado directamente sobre

los proveedores de GCP para evitar dependencias adicionales.

El flujo completo es: (1) el cliente hace POST /jobs con los parámetros del análisis

→ (2) la API persiste el job en la base de datos (estado: QUEUED) y lo encola en

Redis/Pub-Sub → (3) el worker, que escucha la cola, consume el mensaje → (4)

instancia el analizador que ejecuta el pipeline de visión → (5) guarda resultados en

el proveedor de almacenamiento configurado (filesystem local o GCS) → (6)

actualiza el estado del job en la base de datos a COMPLETED → (7) el cliente puede

hacer GET /jobs/{id} para consultar estado y GET /jobs/{id}/results para

obtener los resultados.

La abstracción de providers es el aspecto de diseño más importante de esta capa.

Los providers son interfaces Python con implementaciones intercambiables:

•  StorageProvider: LocalStorage (local), GCSStorage (Google Cloud

Storage), MemoryStorage (caché en memoria).

•  QueueProvider: InMemoryQueue (implementación en memoria para

desarrollo), RedisQueue (producción), GCPubSubQueue (Google Cloud Pub/Sub).

•  DatabaseProvider: SQLAlchemy con adaptadores para SQLite (local) y

PostgreSQL (cloud).

Al  inyectar  los  providers  como  dependencias  de  FastAPI,  el  código  de  negocio

abstracta. Esto hace que los tests de integración puedan sustituir los providers reales

por mocks en memoria, sin necesidad de una infraestructura cloud real para ejecutar

el test suite.

El  núcleo  analítico  nunca  importa  directamente  GCS  ni  Redis:  solo  habla  con  la

interfaz de los proveedores, garantizando la portabilidad entre entornos.

Tabla 19. Comparativa entre arquitectura monolítica y arquitectura desacoplada API + worker.

Aspecto

Arquitectura monolítica

Arquitectura desacoplada

Arquitectura

Monolítica: UI + lógica + análisis en un

proceso

Escalabilidad

Bloqueo por análisis en hilo HTTP

Jobs asíncronos, múltiples workers

posibles

Persistencia

En memoria / filesystem directo

ORM relacional + capa de almacenamiento
local o en la nube (configurable)

Testabilidad

Difícil aislar componentes

Providers inyectables; tests de integración

Despliegue

No diseñado para Cloud Run

Dos imágenes Docker independientes

cloud

WebSocket

WebSocket nativo en el servidor
monolítico

Polling SSE + WS opcional vía

worker callback

Variables de entorno operativas
Tabla 20. Variables de entorno operativas clave.

Variable

Valor por defecto

Descripción

MODEL_PATH

weights/best.pt

Ruta al modelo YOLO principal

DATABASE_URL

sqlite:///./

Cadena de conexión SQLAlchemy

runtime_data/jobs.db

STORAGE_BACKEND

filesystem

filesystem |  gcs |  redis

GCS_BUCKET

—

Nombre del bucket GCS (solo si

STORAGE_BACKEND=gcs)

QUEUE_BACKEND

local

local |  redis |  pubsub

ANTHROPIC_API_KEY  —

Activar narrativa LLM (opcional)

BATCH_SIZE_SECONDS  3

Duración del micro-lote de análisis

en segundos

YOLO_IMGSZ

640

Tamaño de imagen para inferencia

         ANEXO I

    Resultados completos de evaluación

Alcance temporal del sistema: definición de «tiempo casi
real»

El  término  «tiempo  real»  admite  al  menos  tres  acepciones  en  la  literatura  de

sistemas de cómputo y visión artificial, con implicaciones muy distintas para el diseño

del sistema:

  Tiempo real estricto (hard real-time): el sistema garantiza que cada fotograma es
procesado dentro de un  plazo determinista antes de que llegue el siguiente. Para
vídeo a 25 fps esto implica completar detección, tracking, homografía y métricas en
menos de 40 ms por fotograma. Ninguna configuración de hardware de consumo
probada en este proyecto alcanza ese umbral con el pipeline completo activado.
  Tiempo real suave (soft real-time): se toleran ocasionales incumplimientos del plazo
sin que el sistema falle, pero el valor de los resultados degradados sigue siendo útil.
Los sistemas de broadcast deportivo  comerciales (Tracab, STATS  Edge) operan en
este régimen mediante hardware GPU de alto rendimiento dedicado.

  Baja  latencia  incremental  (near  real-time  o  quasi-tiempo  real):  el  vídeo  se
segmenta  en  micro-lotes  de  3  s  y  los  resultados  parciales  se  envían  al  cliente  vía
WebSocket conforme se completan. La latencia del primer resultado es del orden de
segundos, no de fotogramas. Este es el régimen en que opera TacticAI.

La  elección  del  tercer  régimen  responde  a  las  restricciones  reales  del  proyecto:

hardware  de  consumo  (CPU/GPU  estándar),  vídeo  de  retransmisión  a  resolución

completa  y  un  pipeline  que  combina  detección  YOLO,  tracker  multi-objeto,

estimación de homografía y cálculo de métricas tácticas en cada lote. Dentro de este

régimen,  TacticAI  ofrece  retroalimentación  continua  y  progresiva  muy  superior  al

análisis  offline  convencional.  Las  métricas  cuantitativas  que

justifican  esta

clasificación —velocidad de inferencia, fps efectivos del pipeline, relación tiempo-de-

análisis/duración-del-vídeo  y  latencia  del  primer  resultado—  se  detallan  en  las

secciones siguientes.

Métricas del detector principal

El modelo detector principal fue evaluado exhaustivamente sobre el conjunto de test

reservado (no visto durante el entrenamiento ni la validación). El conjunto de test

contiene 9 621 imágenes con 104 516 instancias etiquetadas, distribuidas en cuatro

clases: player (80 %), ball (7 %), referee (7 %) y goalkeeper (6 %).

La velocidad de inferencia es de 26,4 ms por imagen (0,8 ms preproceso + 26,4 ms

YOLO  +  0,8  ms  postproceso  =  28  ms  total  por  imagen).  Este  tiempo  incluye  la

transferencia de la imagen a VRAM, la inferencia completa de la red YOLO11m y el

procesado NMS de las cajas de salida.

Antes  de  analizar  los  resultados  tabla  a  tabla,  conviene  definir  con  precisión  las

métricas:

  Precisión (P) a umbral de confianza óptimo: de las detecciones emitidas, fracción
que son verdaderos positivos. Se calcula al umbral de confianza que maximiza F1.
  Recall  (R)  a  umbral  de  confianza  óptimo:  de  los  objetos  reales,  fracción  que  fue

detectada. Complementa a P.

  mAP@0.5: mean Average Precision con IoU≥0.5 como criterio de detección correcta.

Permite comparar con benchmarks externos en la misma métrica.

  mAP@0.5:0.95 (COCO AP): promedio de AP sobre 10 umbrales IoU [0.5,  0.55, ...,
0.95]. Métrica canónica de COCO más exigente; penaliza localizaciones imprecisas
aunque el objeto sea identificado correctamente.

El resultado global es mAP@0.5 = 0,893, que es un resultado sólido para el dominio

del fútbol. Los detectores comerciales de referencia suelen operar en el rango 0,85–

0,95  mAP@0.5  para  las  mismas  clases.  El  análisis  clase  a  clase  revela  los  puntos

fuertes y débiles del sistema:

• Player (mAP@0.5=0.971): el resultado más alto, esperable dado que es la clase

con  más  instancias  y  que  los  jugadores  tienen  apariencia  relativamente

consistente (silueta humana erguida, bounding box bien definido). El recall de

0.938 indica que el sistema detecta el 93.8% de los jugadores en el conjunto

de test.

• Ball (mAP@0.5=0.800): el  resultado más bajo y el mayor  desafío técnico. El

balón es el objeto más pequeño de la escena (puede ocupar 10×10 px en planos

generales),  tiene  apariencia  variable  según  el  ángulo  y  la  velocidad  (motion

blur), y está frecuentemente oculto por jugadores en jugadas de área. El recall

de 0.731 implica que el 27% de las instancias del balón no son detectadas. Para

el pipeline, esto se mitiga parcialmente con el tracker que interpola la posición

del balón en fotogramas donde no es detectado.

• Referee (mAP@0.5=0.944): alto, gracias a que el árbitro viste equipación de

color  muy  distintivo  (negro  o  amarillo/verde  lima)  que  lo  diferencia

claramente de los jugadores. El sistema lo detecta correctamente en la gran

mayoría de fotogramas.

• Goalkeeper (mAP@0.5=0.856): moderado-alto. El portero presenta más

variabilidad de apariencia (distintos colores de equipación por partido) y

con frecuencia aparece en posturas atípicas (en el suelo, saltando) que el

modelo ha visto menos durante el entrenamiento.

Tabla 21. Métricas de evaluación del detector principal — YOLO11m, imgsz 640.

Imágenes

Instancias

P

R

mAP@0.5

mAP@0.5:0.95

Clase

All

player

ball

referee

9 621

9 485

7 510

5 057

104 516

0.891

0.846

0.893

0.645

83 547

0.952

0.938

0.971

7 517

7 528

5 924

0.847

0.731

0.800

0.923

0.898

0.944

0.842

0.817

0.856

0.757

0.487

0.722

0.615

goalkeeper

5 723

Métricas del modelo de keypoints

El modelo de keypoints fue evaluado sobre un conjunto de test de 498 imágenes con

4 349 instancias de puntos de referencia del campo. La velocidad de inferencia es de

solo 10.3 ms por imagen, significativamente menor que el detector principal porque

este modelo fue entrenado con

pero con output de puntos clave (más ligero que

bounding boxes), y la arquitectura YOLO11m se adapta bien a esta tarea.

• Keypoints  de  alta  dificultad  (corner,  mAP@0.5=0.894):  las  esquinas  del

campo son  las  más  difíciles  porque:  (i)  pueden  estar  fuera  del  cuadro  de

cámara en planos cerrados; (ii) su apariencia varía mucho según el ángulo de

perspectiva; (iii) en algunos estadios las esquinas están marcadas solo con un

banderín, sin líneas que ayuden a localizar el punto exacto.

• Keypoints

de

alta

precisión

(halfcircle_top,  mAP@0.5=0.991;

midline_top_intersection, mAP@0.5=0.987): los puntos del círculo central y

las intersecciones de la línea media son los más fáciles: son visibles desde la

perspectiva típica de la cámara principal, tienen marcas geométricas claras en

el campo, y están en el centro del encuadre donde la distorsión de perspectiva

es menor.

• bigarea_bottom_outter  (solo  62  instancias):  esta  clase  tiene  muy  pocas

instancias de entrenamiento porque el área grande de la portería inferior solo

es visible cuando la cámara está en el extremo opuesto del campo. A pesar de

esto, el modelo alcanza mAP@0.5=0.971, lo que indica que las pocas instancias

disponibles eran suficientemente representativas.

La combinación  de los dos modelos (detector +  keypoints) en el pipeline añade un

overhead  de  10.3  ms  por  fotograma  al  tiempo  total  de  procesamiento  cuando  la

homografía está activa.

Tabla 22. Métricas de evaluación del modelo de keypoints — YOLO11m, imgsz 960.

Clase (keypoint)

Imágenes

Instancias

P

R

mAP@0.5  mAP@0.5:0.95

All

corner

top_arc_area_intersection

498

401

403

bottom_arc_area_intersection  380

bigarea_bottom_inner

midline_top_intersection

halfcircle_top

halfcircle_bottom

321

184

186

189

midline_bottom_intersection

122

bigarea_top_outter

smallarea_top_outter

smallarea_bottom_outter

bigarea_bottom_outter

smallarea_top_inner

smallarea_bottom_inner

bigarea_top_inner

385

341

252

62

369

296

372

4 349

0.940

0.934

0.956

0.663

415

425

385

323

185

186

189

127

387

342

252

62

370

296

405

0.893

0.866

0.894

0.587

0.943

0.931

0.955

0.650

0.936

0.919

0.941

0.641

0.952

0.963

0.984

0.726

0.967

0.984

0.987

0.704

0.968

0.982

0.991

0.730

0.971

0.968

0.966

0.716

0.933

0.879

0.933

0.606

0.896

0.873

0.907

0.595

0.930

0.930

0.942

0.633

0.945

0.950

0.976

0.689

0.924

0.935

0.971

0.619

0.941

0.922

0.960

0.699

0.956

0.961

0.973

0.703

0.951

0.950

0.956

0.643

Tabla 23. Benchmarks de rendimiento del pipeline completo por configuración de hardware.

Hardware

imgsz

YOLO infer. (ms/

Pipeline completo

FPS

vs. 25 fps real-

img)

(ms/frame)

efectivo

time

RTX 5070 Ti Laptop

640

26.4 (medido)

~60–65

~15–17

~0.65× (≈1.5×

(12 GB)

duración)

RTX 4070 (8 GB

640

~20 (estimado)

~50–55

~18–20

~0.75×

VRAM)

RTX 3060 (6 GB

640

~32 (estimado)

~70–80

~12–14

~0.55×

VRAM)

RTX 3060

1280

~80 (estimado)

~130–150

CPU Intel i7-12gen

640

~200

~300–400

(sin GPU)

(estimado)

~6–7

~2–3

~0.27×

~0.1×

Nota  sobre  rendimiento:  Los  valores  de "Pipeline completo"  incluyen  YOLO,  Re-ID  (~10  ms),

TeamClassifier  (~5  ms),  PossessionTracker  (~3  ms),  HeatmapSystem  (~4  ms),  serialización  de

MatchState  (~3  ms)  y  overhead  de  micro-lote.  El  RTX  5070  Ti  procesa  cada  fotograma  en

aproximadamente 60–65 ms en conjunto, lo que supone una velocidad efectiva de ~16 FPS —

equivalente a procesar 1 segundo de vídeo en ~1.5 segundos de cómputo (+0.5× sobre tiempo

real). Esto descarta el procesamiento truly frame-a-frame en tiempo real pero sí permite analizar

un partido de 90 minutos en aproximadamente 135 minutos, con resultados disponibles en baja

latencia gracias al micro-batching.

Rendimiento del pipeline completo

El resultado más importante que comunicar respecto al rendimiento es la diferencia

entre  la  velocidad  de  inferencia  YOLO  aislada  y  la  velocidad  efectiva  del  pipeline

completo. Esta diferencia es sustancial y relevante para las expectativas del usuario.

La inferencia YOLO sola en el RTX 5070 Ti tarda 26.4 ms por fotograma (≈38 fps), pero

el pipeline completo opera a aproximadamente 60–65 ms por fotograma (≈16 fps). La

diferencia (~35 ms por fotograma) se distribuye aproximadamente así:

• ReID  Tracker  (~10  ms):  extracción  de  embeddings  de  apariencia  para  N

detecciones + cálculo de la matriz de costes + algoritmo húngaro. El coste escala

con el número de tracks activos (típicamente 22–30 en un partido).

• Clasificador de equipos (~5 ms):  conversión de ROIs a LAB, aplicación de

máscaras,  extracción  de  histogramas  de  color,  KMeans.  La  mayoría  del

tiempo se gasta en la conversión de espacio de color vía OpenCV.

• PossessionTracker  (~3  ms):  cálculos  de  distancia  euclidiana  entre

posiciones  del  balón  y  todos  los  jugadores,  aplicación  de  histéresis

temporal.

• HeatmapSystem  +  KeypointDetector  (~12  ms):  inferencia  del  modelo  de

keypoints  (10.3  ms)  +  cálculo  de  homografía  +  acumulación  de  heatmaps

proyectados al campo.

• Serialización  de  MatchState  y  envío  WebSocket  (~3  ms):  conversión  a

diccionario Python, serialización JSON, envío por socket.

• Overhead del lote y gestión de frames (~2 ms): lectura desde el iterador de

vídeo, gestión de memoria, copias de arrays NumPy.

El resultado final es que para el hardware de prueba (RTX 5070 Ti Laptop), el sistema

procesa 1 segundo de vídeo en aproximadamente 1.5 segundos de cómputo. Para

un  partido  de  90  minutos,  el  análisis  completo  tomaría  aproximadamente  135

minutos. Con el micro-batching, el usuario empieza a recibir resultados en el browser

a los ~5 segundos del inicio del procesamiento, y obtiene actualizaciones progresivas

cada ~4–5 segundos.

Para hardware más potente (workstation con RTX 4090 o estación de análisis de vídeo

profesional), se estima que el pipeline podría operar cerca del tiempo real (~25 fps

efectivos).  Para  entornos  de  análisis  masivo  (múltiples  partidos  en  paralelo),  la

arquitectura dual API permite distribuir el trabajo en varios workers con diferentes

GPUs.

La  Figura  13  muestra  el  FPS  efectivo  del  pipeline  completo  por  configuración  de

hardware.  Se  observa  que  ninguna  configuración  de  la  lista  alcanza  los  25  fps

necesarios  para  tiempo  real  estricto  en  el  hardware  de  consumo  probado.  Esto

refuerza  la  conclusión  de  que  TacticAI  es  un  sistema  de  análisis  en  diferido  con

actualización incremental, no un sistema de tiempo real estricto.

Figura 12. Curvas de entrenamiento del detector YOLO11m — mAP@0.5 = 0.893 y mAP@0.5:0.95 = 0.645 al final de
las 100 épocas. Los valores finales coinciden con los medidos en evaluación (Tabla 19).

Figura 13. FPS del pipeline completo por configuración de hardware. La línea roja indica 25 fps (umbral de tiempo
real). Los valores incluyen YOLO, Re-ID, TeamClassifier, posesión, heatmaps y serialización. El RTX 5070 Ti
procesa a ~16 FPS en pipeline completo (~1.5× duración del vídeo). Ver Tabla 21.

