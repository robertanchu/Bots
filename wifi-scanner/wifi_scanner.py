#!/usr/bin/env python3
"""
WiFi Scanner Bot para Android (Termux)
=======================================

Escáner PASIVO de redes WiFi: lee los beacons que las redes cercanas ya
emiten públicamente (SSID, BSSID, canal, señal, tipo de cifrado).

No intenta conectarse a ninguna red, no envía ningún paquete, no prueba
contraseñas. Es el mismo tipo de información que muestra cualquier app de
"análisis WiFi" de la Play Store o el propio selector de redes de Android.

Requisitos:
  - Termux (F-Droid): https://f-droid.org/packages/com.termux/
  - Termux:API (F-Droid): https://f-droid.org/packages/com.termux.api/
  - En Termux:  pkg install termux-api python
  - Conceder a Termux:API el permiso de Ubicación en Android (obligatorio
    por el sistema operativo para poder leer resultados de escaneo WiFi).

Uso:
  python wifi_scanner.py scan                 # listado único
  python wifi_scanner.py radar                # intensidad de señal en vivo
  python wifi_scanner.py watch                # vigilancia + alertas + log
  python wifi_scanner.py watch --known home.json
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

DATA_DIR = Path.home() / ".wifi_scanner"
LOG_FILE = DATA_DIR / "history.jsonl"
KNOWN_FILE = DATA_DIR / "known_networks.json"


# ---------------------------------------------------------------------------
# Captura de datos vía Termux:API
# ---------------------------------------------------------------------------

def run_scan():
    """Ejecuta termux-wifi-scaninfo y devuelve la lista de redes detectadas.

    termux-wifi-scaninfo expone los resultados del último escaneo WiFi que
    el propio sistema Android ya realiza. Es una lectura pasiva, equivalente
    a 'ver qué redes hay' en los ajustes de WiFi del teléfono.
    """
    try:
        raw = subprocess.check_output(
            ["termux-wifi-scaninfo"], stderr=subprocess.DEVNULL, timeout=15
        )
    except FileNotFoundError:
        sys.exit(
            "Error: no se encontró 'termux-wifi-scaninfo'.\n"
            "Instala Termux:API con: pkg install termux-api\n"
            "y la app Termux:API desde F-Droid (debe estar instalada además del paquete)."
        )
    except subprocess.CalledProcessError as e:
        sys.exit(f"Error ejecutando termux-wifi-scaninfo: {e}")
    except subprocess.TimeoutExpired:
        sys.exit("Timeout esperando resultados de escaneo WiFi.")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(
            "No se pudo leer la respuesta de termux-wifi-scaninfo.\n"
            "Comprueba que has concedido permiso de Ubicación a Termux:API\n"
            "en Ajustes > Apps > Termux:API > Permisos."
        )

    networks = []
    for ap in data:
        networks.append(
            {
                "ssid": ap.get("ssid") or "(oculta)",
                "bssid": ap.get("bssid", "??"),
                "frequency": ap.get("frequency", 0),
                "channel": freq_to_channel(ap.get("frequency", 0)),
                "rssi": ap.get("level", ap.get("rssi", -100)),
                "capabilities": ap.get("capabilities", ""),
                "security": classify_security(ap.get("capabilities", "")),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        )
    return sorted(networks, key=lambda n: n["rssi"], reverse=True)


def freq_to_channel(freq):
    """Convierte frecuencia (MHz) a número de canal WiFi (2.4GHz y 5GHz)."""
    if not freq:
        return "?"
    if 2412 <= freq <= 2484:
        return (freq - 2412) // 5 + 1 if freq != 2484 else 14
    if 5170 <= freq <= 5825:
        return (freq - 5000) // 5
    return "?"


def classify_security(caps: str) -> str:
    caps = caps.upper()
    if "WPA3" in caps or "SAE" in caps:
        return "WPA3"
    if "WPA2" in caps or "RSN" in caps:
        return "WPA2"
    if "WPA" in caps:
        return "WPA"
    if "WEP" in caps:
        return "WEP (inseguro)"
    if caps.strip() in ("", "[ESS]"):
        return "Abierta (sin cifrado)"
    return caps


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def rssi_bar(rssi: int, width: int = 20) -> str:
    """Barra visual de intensidad de señal: -30 dBm (excelente) a -100 dBm (nula)."""
    pct = max(0.0, min(1.0, (rssi + 100) / 70))
    filled = int(pct * width)
    return "█" * filled + "░" * (width - filled)


def cmd_scan(args):
    networks = run_scan()
    if not networks:
        print("No se detectaron redes WiFi cercanas.")
        return
    print(f"{'SSID':<24} {'BSSID':<18} {'Canal':>5} {'dBm':>5}  {'Señal':<22} Seguridad")
    print("-" * 95)
    for n in networks:
        print(
            f"{n['ssid'][:24]:<24} {n['bssid']:<18} {str(n['channel']):>5} "
            f"{n['rssi']:>5}  {rssi_bar(n['rssi']):<22} {n['security']}"
        )


def cmd_radar(args):
    target = args.ssid
    print("Radar de intensidad de señal — Ctrl+C para salir")
    if target:
        print(f"Filtrando por SSID: {target}")
    try:
        while True:
            networks = run_scan()
            if target:
                networks = [n for n in networks if n["ssid"] == target]
            print("\033c", end="")  # limpia pantalla
            print(f"Radar WiFi — {datetime.now().strftime('%H:%M:%S')}\n")
            if not networks:
                print("(sin coincidencias)")
            for n in networks:
                print(f"{n['ssid'][:20]:<20} {n['rssi']:>5} dBm  {rssi_bar(n['rssi'], 30)}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nDetenido.")


def load_known():
    if KNOWN_FILE.exists():
        return json.loads(KNOWN_FILE.read_text())
    return {}


def save_known(known):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    KNOWN_FILE.write_text(json.dumps(known, indent=2, ensure_ascii=False))


def notify(title: str, message: str):
    try:
        subprocess.run(
            ["termux-notification", "--title", title, "--content", message],
            check=False,
            timeout=5,
        )
    except FileNotFoundError:
        pass  # termux-notification no disponible; seguimos solo con stdout
    print(f"[ALERTA] {title}: {message}")


def cmd_watch(args):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    known = load_known()
    seen_this_run = set()
    print(f"Vigilando redes WiFi cada {args.interval}s — log en {LOG_FILE}")
    print("Ctrl+C para salir\n")

    try:
        while True:
            networks = run_scan()
            now_bssids = set()

            with LOG_FILE.open("a") as f:
                for n in networks:
                    now_bssids.add(n["bssid"])
                    f.write(json.dumps(n, ensure_ascii=False) + "\n")

                    if n["bssid"] not in known:
                        notify(
                            "Red nueva detectada",
                            f"{n['ssid']} ({n['bssid']}) {n['rssi']}dBm {n['security']}",
                        )
                        known[n["bssid"]] = {
                            "ssid": n["ssid"],
                            "first_seen": n["timestamp"],
                            "security": n["security"],
                        }
                    elif n["bssid"] not in seen_this_run:
                        # Red conocida reapareciendo tras estar ausente
                        pass

            # Detectar redes conocidas que ya no están presentes
            missing = seen_this_run - now_bssids
            for bssid in missing:
                label = known.get(bssid, {}).get("ssid", bssid)
                notify("Red fuera de alcance", f"{label} ({bssid}) ya no se detecta")

            seen_this_run = now_bssids
            save_known(known)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nVigilancia detenida.")


def main():
    parser = argparse.ArgumentParser(description="Escáner pasivo de redes WiFi para Android/Termux")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="Listado único de redes cercanas")
    p_scan.set_defaults(func=cmd_scan)

    p_radar = sub.add_parser("radar", help="Intensidad de señal en tiempo real")
    p_radar.add_argument("--ssid", help="Filtrar por nombre de red (SSID)")
    p_radar.add_argument("--interval", type=float, default=2.0, help="Segundos entre lecturas")
    p_radar.set_defaults(func=cmd_radar)

    p_watch = sub.add_parser("watch", help="Vigilancia continua con alertas e historial")
    p_watch.add_argument("--interval", type=float, default=10.0, help="Segundos entre escaneos")
    p_watch.set_defaults(func=cmd_watch)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
