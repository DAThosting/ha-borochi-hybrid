# Borochi Hybrid Wechselrichter für Home Assistant (Modbus RTU)

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/DEIN-GITHUB-USER/ha-borochi-hybrid/actions/workflows/validate.yaml/badge.svg)](https://github.com/DEIN-GITHUB-USER/ha-borochi-hybrid/actions/workflows/validate.yaml)

Inoffizielle Integration für die dreiphasigen Hochvolt-Hybridwechselrichter **Borochi BHW-8/10/12/15** (BRH008/010/012/015KH-B1) über die RS485-Schnittstelle (Modbus RTU). Lokal, ohne Cloud.

> ## ⚠️ Beta – in Arbeit
> Borochi veröffentlicht **keine Modbus-Registerliste**. Alle Register wurden durch Scannen und Abgleich mit der Borochi-App ermittelt. Deshalb gilt:
>
> - **Nicht alle Werte sind erfasst.** Es fehlen z. B. Netz-, Haus- und Batterieleistung sowie Energiezähler (kWh).
> - Einige Zuordnungen sind **experimentell** (in der Tabelle markiert). Diese Sensoren sind standardmäßig **deaktiviert** und tragen „(experimentell)“ im Namen.
> - Entwickelt und getestet nur mit **BRH015KH-B1** (BHW-15). Andere Modelle: bitte melden, ob es funktioniert.
> - Die Integration **liest nur** und schreibt nie ins Gerät.
> - Nutzung auf eigene Gefahr. Dieses Projekt steht in keiner Verbindung zu Borochi.

## Voraussetzungen

- USB-RS485-Adapter (getestet: CH340) am Home-Assistant-Host
- Verdrahtung laut Handbuch am **COM-Stecker: Pin 7 = RS485 A, Pin 8 = RS485 B** (bei Timeouts A/B tauschen). Nicht den Zähler-, BMS- oder Parallel-Port verwenden.
- Modbus-Adresse **1** (Werkseinstellung; am Gerät unter *Einstellungen → System → Comm Param*)
- Serielle Verbindung: **9600 Baud, 8N1**

Der serielle Port kann nur von **einem** Programm genutzt werden. Eine bestehende `modbus:`-YAML-Konfiguration oder andere Add-ons mit demselben Adapter vorher entfernen oder deaktivieren.

## Installation

### Über HACS (Custom Repository)

1. HACS → ⋮ (oben rechts) → **Benutzerdefinierte Repositories**
2. URL `https://github.com/DEIN-GITHUB-USER/ha-borochi-hybrid`, Kategorie **Integration**
3. „Borochi Hybrid Wechselrichter“ installieren, Home Assistant neu starten
4. *Einstellungen → Geräte & Dienste → Integration hinzufügen → Borochi*

### Manuell

Ordner `custom_components/borochi_hybrid` nach `/config/custom_components/` kopieren und neu starten.

## Einrichtung

| Feld | Beschreibung |
|---|---|
| Serieller Port | Am besten den stabilen Pfad, z. B. `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0` |
| Modbus-Adresse | Standard `1` |
| Baudrate | Standard `9600` |

Das Abfrageintervall (Standard 30 s) lässt sich unter *Konfigurieren* ändern. Zellwerte, Versionen und Seriennummer werden nur alle 10 Minuten gelesen, weil die Leitung langsam ist.

## Sensoren

Status: ✅ bestätigt (mit App verglichen) · 🧪 experimentell (Kandidat, standardmäßig deaktiviert)

| Gruppe | Sensor | Register (Input) | Status |
|---|---|---|---|
| Netz | Spannung L1/L2/L3 | 262/264/266 (×0,1 V) | ✅ |
| Netz | Strom L1/L2/L3 | 263/265/267 (×0,1 A) | ✅ |
| Netz | Spannung L1-L2/L2-L3/L3-L1 | 268–270 (×0,1 V) | ✅ |
| Netz | Frequenz | 271 (×0,01 Hz) | ✅ |
| PV | PV1 Spannung | 208 (×0,1 V) | ✅ |
| PV | PV2 Spannung | 206 (×0,1 V) | ✅ |
| PV | PV1/PV2 Strom | 223 / 225 (×0,01 A) | 🧪 |
| PV | PV1/PV2 Leistung | berechnet U·I | 🧪 |
| Batterie | Spannung | 529 (×0,1 V) | ✅ |
| Batterie | SOC | 533 (×0,1 %) | ✅ |
| Batterie | SOH | 534 (×0,1 %) | ✅ |
| Batterie | Zyklen | 535 | ✅ |
| Batterie | Temperatur | 536 (×0,1 °C) | ✅ |
| Batterie | Kapazität | 1905 (×0,1 kWh) | ✅ |
| Batterie | BMS-Temperatur | 538 (×0,1 °C) | 🧪 |
| Batterie | Strom | 570 (×0,01 A) | 🧪 |
| Zellen | Min/Max/Spreizung (128 Zellen) | 2300–2427 (mV) | ✅ |
| Zellen | Temperatur min/max | 2428–2445 (×0,1 °C) | ✅ |
| Info | Modell, Seriennummer | 0–5, 16–23 (ASCII) | ✅ |
| Info | Firmware Haupt-ARM/Hilfs-ARM/Haupt-DSP | 66 / 68 / 70 (gepackt) | ✅ |
| Info | Nennleistung | 61 (W) | ✅ |

### Noch offen

- Netz-/Einspeiseleistung, Haus- und Batterieleistung (Kandidaten im Bereich 700–740, 32 Bit vorzeichenbehaftet)
- Energiezähler (Tages- und Gesamtenergie) für das Energie-Dashboard
- Betriebsstatus und Fehlercodes
- BMS-Version, Batterie-Seriennummer, Wallbox
- Steuerung (Betriebsmodus etc.): bewusst noch nicht vorgesehen

Bis Energiezähler vorhanden sind, kannst du aus einem Leistungssensor mit dem Helfer **Integral-Sensor (Riemann-Summe)** einen kWh-Wert für das Energie-Dashboard erzeugen.

## Fehlersuche

- **Keine Verbindung / Timeout:** Port von anderen Programmen belegt? A/B getauscht? Adresse und Baudrate am Gerät prüfen. Bei HA OS ist der by-id-Pfad zuverlässiger als `/dev/ttyUSB0`.
- **Sensoren `unbekannt`:** Bei Nacht oder Standby antwortet das Gerät teilweise nicht. Intervall erhöhen.
- **Debug-Log:**
  ```yaml
  logger:
    logs:
      custom_components.borochi_hybrid: debug
  ```

## Mithelfen

Am meisten helfen **Registerdaten mit passenden App-Werten** vom gleichen Zeitpunkt (Register, Rohwert, App-Wert), besonders für andere Modelle (8/10/12 kW), Netz-/Hausleistung und Energiezähler. Bitte ein Issue mit der Vorlage „Fehler / Registerdaten melden“ öffnen.

⚠️ **Seriennummern (Wechselrichter, Batterie, Datenlogger) vor dem Posten entfernen.**

## Haftungsausschluss

Inoffizielles Community-Projekt, nicht mit Borochi verbunden oder von Borochi unterstützt. „Borochi“ ist eine Marke ihres Inhabers. Die Integration greift ausschließlich lesend zu, dennoch erfolgt die Nutzung auf eigenes Risiko. Elektrische Arbeiten am Gerät nur durch Elektrofachkräfte.

## Lizenz

MIT
