# Borochi Hybrid Wechselrichter für Home Assistant (Modbus RTU)

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/DAThosting/ha-borochi-hybrid/actions/workflows/validate.yaml/badge.svg)](https://github.com/DAThosting/ha-borochi-hybrid/actions/workflows/validate.yaml)

Inoffizielle Integration für die dreiphasigen Hochvolt-Hybridwechselrichter **Borochi BHW-8/10/12/15** (BRH008/010/012/015KH-B1) über die RS485-Schnittstelle (Modbus RTU). Lokal, ohne Cloud.

> ## ⚠️ Beta – in Arbeit
> Borochi veröffentlicht keine öffentliche Modbus-Registerliste. Alle Register wurden durch Scannen des Geräts und Abgleich der Werte mit der Borochi-App ermittelt. Deshalb gilt:
>
> - Ab Version 0.3.0 sind die zentralen Werte (PV, Netz, Haus, Batterie, Energiezähler, Status) mit hoher Zuversicht zugeordnet und rechnerisch gegengeprüft (z. B. PV-Spannung × Strom ergibt die gemeldete PV-Leistung). Einzelne Details (Fehler-/Warncodes, EPS-Werte) fehlen noch oder sind als „experimentell“ markiert.
> - Entwickelt und getestet nur mit **BRH015KH-B1** (BHW-15). Andere Modelle: bitte melden, ob es funktioniert.
> - Die Integration **liest nur** und schreibt nie ins Gerät.
> - Nutzung auf eigene Gefahr. Dieses Projekt steht in keiner Verbindung zu Borochi.
> - Register-Zuordnungen können sich in künftigen Versionen noch ändern, wenn sich neue Erkenntnisse ergeben – bitte nach einem Update die Energie-Dashboard-Zuordnung und eigene Automationen kurz prüfen.

## Voraussetzungen

- USB-RS485-Adapter (getestet: CH340) am Home-Assistant-Host
- Verdrahtung laut Handbuch am **COM-Stecker: Pin 7 = RS485 A, Pin 8 = RS485 B** (bei Timeouts A/B tauschen). Nicht den Zähler-, BMS- oder Parallel-Port verwenden.
- Modbus-Adresse **1** (Werkseinstellung; am Gerät unter *Einstellungen → System → Comm Param*)
- Serielle Verbindung: **9600 Baud, 8N1**

Der serielle Port kann nur von **einem** Programm genutzt werden. Eine bestehende `modbus:`-YAML-Konfiguration oder andere Add-ons mit demselben Adapter vorher entfernen oder deaktivieren.

### Name der USB-Schnittstelle herausfinden

Nutze möglichst den stabilen Pfad unter `/dev/serial/by-id/`. Anders als `/dev/ttyUSB0` ändert er sich nicht, wenn du den Adapter an einen anderen USB-Port steckst oder neu startest.

```bash
ls -l /dev/serial/by-id/
```
Beispiel: `usb-1a86_USB_Serial-if00-port0 -> ../../ttyUSB0`. Als Port trägst du dann `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0` ein.

Erscheint nichts: Adapter aus- und wieder einstecken, danach `dmesg | tail` prüfen.

### Docker: USB-Adapter durchreichen

Läuft Home Assistant in Docker, muss der Adapter dem Container über `devices` durchgereicht werden:

```yaml
services:
  homeassistant:
    devices:
      - /dev/serial/by-id/usb-1a86_USB_Serial-if00-port0:/dev/ttyUSB0
```

Als **Serieller Port** trägst du in der Integration dann `/dev/ttyUSB0` ein (den Namen im Container). Nach Ändern der `devices`-Zeile muss der Container neu erstellt werden (`docker compose up -d`), ein Neustart reicht nicht. Der Adapter darf nur von einem Container/Programm gleichzeitig genutzt werden.

## Installation

### Über HACS (Custom Repository)

1. HACS → ⋮ (oben rechts) → **Benutzerdefinierte Repositories**
2. URL `https://github.com/DAThosting/ha-borochi-hybrid`, Kategorie **Integration**
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

Unter *Konfigurieren* lassen sich das Abfrageintervall (Standard 30 s) und „Vorzeichen der Netzleistung umkehren“ einstellen. Standardmäßig gilt: **positiv = Netzbezug, negativ = Einspeisung** (Home-Assistant-Konvention). Die Option ist für den Fall gedacht, dass die Zählerverdrahtung bei dir umgekehrt ist.

## Sensoren

Als „🧪 experimentell“ markierte Sensoren sind standardmäßig **deaktiviert** (unter *Einstellungen → Geräte & Dienste → Entitäten* aktivierbar), weil Bedeutung oder Vorzeichen noch nicht mit Messwerten abgeglichen sind.

### PV
| Sensor | Register | Format |
|---|---|---|
| PV Gesamtleistung | 220-221 | 32 Bit, W |
| PV1/PV2 Spannung | 222 / 224 | ×0,1 V |
| PV1/PV2 Strom | 223 / 225 | ×0,01 A |
| PV1/PV2 Leistung | berechnet U·I | W |
| PV Ertrag heute/gesamt | 501-502 / 503-504 | 32 Bit, ×0,1 kWh |

### Netz
| Sensor | Register | Format |
|---|---|---|
| Netzleistung, Einspeisung, Netzbezug | 274-275 | 32 Bit, ×1 W (+ = Bezug, − = Einspeisung) |
| Netzspannung/-strom L1-L3 | 262-267 | ×0,1 V / ×0,1 A |
| Netzfrequenz | 271 | ×0,01 Hz |
| Netzbezug/Einspeisung Energie (Zähler) | 729-730 / 731-732 | 32 Bit, ×0,01 kWh |
| Netzbezug Energie heute/gesamt (Wechselrichter) | 505-506 / 507-508 | 32 Bit, ×0,1 kWh |
| Netz Blindleistung, Scheinleistung, Leistungsfaktor | 272-273, 276-277, 278 | Diagnose |

### Haus
| Sensor | Register | Format |
|---|---|---|
| Hausverbrauch | 569-570 | 32 Bit, W |
| Hausverbrauch Energie heute/gesamt | 571-572 / 573-574 | 32 Bit, ×0,1 kWh |

### Batterie
| Sensor | Register | Format |
|---|---|---|
| Spannung, Strom, Leistung | 529 / 530 / 531-532 | ×0,1 V, ×0,1 A, W; + = Laden, − = Entladen |
| SOC, SOH, Zyklen | 533 / 534 / 535 | ×0,1 % / ×0,1 % / Anzahl |
| Temperatur, BMS-Temperatur | 536 / 538 | ×0,1 °C |
| Zellspannung min/max/Spreizung | 565 / 564 / berechnet | ×0,001 V |
| Lade-/Entladeenergie heute/gesamt | 544-551 | 32 Bit, ×0,1 kWh |
| Kapazität, Seriennummer, BMS-Version | 1905, 1908-1923, 1906-1907 | Diagnose |

### Wechselrichter / Status
| Sensor | Register | Format |
|---|---|---|
| Status, Betriebsmodus, Fehler-/Warnstatus | 200, 500, 279-290 | Text (siehe unten) |
| Modell, Seriennummer, Nennleistung, Modbus-Adresse | 0-31, 60-61, 63 | Diagnose |
| Firmware Haupt-ARM/Hilfs-ARM/Haupt-DSP, Hardware-Version | 66/68/70, 64 | gepackt, z. B. V10.10.020 |
| Wechselrichter-/Umgebungstemperatur, Zwischenkreisspannung | 210, 211, 215 | Diagnose |

**Fehler-/Warnstatus:** zeigt bei aktivem Fehler die rohen Registerwerte (z. B. `Reg281=0x0004`), noch ohne Klartext-Übersetzung der einzelnen Bits.

### Noch offen
- Klartext-Übersetzung der Fehler-/Warncodes
- EPS-Werte (Notstrom/Inselbetrieb)
- Zeitplan-Einstellungen (Lade-/Entladefenster) als Sensoren
- Bestätigung an weiteren Modellen (8/10/12 kW)

Die vollständige Liste der 128 Einzel-Zellspannungen wird aus Effizienzgründen (langsame RS485-Verbindung) nicht mehr ausgelesen – stattdessen liefert das Gerät Min/Max direkt.

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

Am meisten helfen **Registerdaten mit passenden App-Werten** vom gleichen Zeitpunkt (Register, Rohwert, App-Wert), besonders für andere Modelle (8/10/12 kW) sowie EPS-Werte und Fehlercodes. Bitte ein Issue mit der Vorlage „Fehler / Registerdaten melden“ öffnen.

⚠️ **Seriennummern (Wechselrichter, Batterie, Datenlogger) vor dem Posten entfernen.**

## Haftungsausschluss

Inoffizielles Community-Projekt, nicht mit Borochi verbunden oder von Borochi unterstützt. „Borochi“ ist eine Marke ihres Inhabers. Die Integration greift ausschließlich lesend zu, dennoch erfolgt die Nutzung auf eigenes Risiko. Elektrische Arbeiten am Gerät nur durch Elektrofachkräfte.

## Lizenz

MIT
