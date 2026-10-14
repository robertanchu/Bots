# WiFi Scanner Bot (Android / Termux)

Escáner **pasivo** de redes WiFi cercanas: SSID, BSSID, canal, intensidad de
señal (dBm) y tipo de cifrado. No se conecta a ninguna red, no envía
paquetes de autenticación, no prueba contraseñas. Lee exactamente la misma
información que ya muestra el selector de WiFi de Android, solo que con más
detalle y guardándola.

## ⚠️ Qué es y qué no es esta herramienta

- ✅ Reconocimiento pasivo de redes al alcance de tu antena WiFi (igual que
  cualquier app "WiFi Analyzer" de la Play Store).
- ✅ Útil para: elegir el mejor canal para tu router, localizar físicamente
  un punto de acceso (el tuyo), detectar si aparece un dispositivo/AP nuevo
  en tu vivienda, llevar un registro de qué redes ves y cuándo.
- ❌ **No** intenta obtener contraseñas de ninguna red.
- ❌ **No** incluye ni incluirá ataques de fuerza bruta, diccionario,
  captura de handshakes o desautenticación. Usar estas técnicas contra
  redes que no son tuyas es ilegal en la gran mayoría de jurisdicciones
  (acceso no autorizado a sistemas informáticos).

Si necesitas auditar la seguridad de **tu propia** red (por ejemplo, para
comprobar si tu contraseña es débil), hazlo con herramientas dedicadas de
pentesting (aircrack-ng, hashcat) en un entorno que controles, nunca con
este script ni contra redes ajenas.

## Requisitos

1. Instala **Termux** desde F-Droid (no la versión de Play Store, está
   desactualizada): https://f-droid.org/packages/com.termux/
2. Instala **Termux:API** desde F-Droid, es una app aparte:
   https://f-droid.org/packages/com.termux.api/
3. En Termux:

   ```bash
   pkg update && pkg upgrade
   pkg install termux-api python
   ```

4. Concede permiso de **Ubicación** a la app Termux:API en:
   Ajustes de Android → Apps → Termux:API → Permisos → Ubicación.
   Android exige este permiso a cualquier app para leer resultados de
   escaneo WiFi (es una política del sistema operativo, no de este bot).

## Instalación del script

```bash
cd ~
git clone <tu-fork-o-repo>
cd Bots/wifi-scanner
```

## Uso

### Listado único

```bash
python wifi_scanner.py scan
```

```
SSID                     BSSID              Canal   dBm  Señal                  Seguridad
-----------------------------------------------------------------------------------------
MiRouter_5G              AA:BB:CC:11:22:33     36   -45  ██████████████░░░░░░  WPA2
Vecino_WiFi              DD:EE:FF:44:55:66      6   -72  ████████░░░░░░░░░░░░  WPA2
CafeteriaPublica         11:22:33:44:55:66      1   -80  ██████░░░░░░░░░░░░░░  Abierta (sin cifrado)
```

### Radar en tiempo real (para localizar físicamente un AP)

```bash
python wifi_scanner.py radar --ssid MiRouter_5G --interval 1
```

Muévete por la casa y observa cómo cambia la barra de señal: más ancho =
más cerca del punto de acceso. Útil para encontrar el sitio óptimo para tu
router o para saber si tu señal llega bien a cierta habitación.

### Vigilancia continua + alertas + historial

```bash
python wifi_scanner.py watch --interval 15
```

- Guarda cada lectura en `~/.wifi_scanner/history.jsonl` (una línea JSON
  por red detectada, con timestamp).
- La primera vez que ve un BSSID lo registra en
  `~/.wifi_scanner/known_networks.json`.
- A partir de ahí, avisa (notificación Android vía `termux-notification` +
  mensaje en terminal) cuando:
  - aparece una red/BSSID nunca visto antes.
  - una red conocida deja de detectarse (sale de alcance o se apaga).

Déjalo corriendo en segundo plano con `tmux` o `termux-wake-lock` si quieres
vigilancia prolongada sin que Android mate el proceso.

## Estructura

```
wifi-scanner/
├── wifi_scanner.py   # script principal (scan / radar / watch)
└── README.md
```

## Notas técnicas

- El canal se calcula a partir de la frecuencia (MHz) reportada por
  Android, válido para bandas 2.4GHz y 5GHz estándar.
- La clasificación de seguridad (WPA2/WPA3/WEP/Abierta) se infiere del
  campo `capabilities` que devuelve `termux-wifi-scaninfo`; en teléfonos
  muy antiguos ese campo puede venir vacío.
- `termux-wifi-scaninfo` solo expone el último escaneo realizado por el
  subsistema WiFi de Android; en versiones recientes de Android el sistema
  limita la frecuencia de escaneos activos por batería, por eso el
  intervalo mínimo recomendado en `watch`/`radar` es de 1-2 segundos como
  mucho más frecuente, y 10-15s para vigilancia prolongada.
