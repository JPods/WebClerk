"""Seed demo items with real open-source hardware products and images.

Replaces HW-* and no-SKU items with real Adafruit products.
Downloads product images from Adafruit CDN (CC BY-SA licensed),
resizes to tn (90px), md (256px), hr (original).

Usage:
    ./bin/python manage.py seed_demo_items --dry-run
    ./bin/python manage.py seed_demo_items
    ./bin/python manage.py seed_demo_items --clean   # remove old HW-*/no-SKU items first
"""
import io
import logging
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger("core.seed_demo_items")

MEDIA_ROOT = Path(getattr(settings, "MEDIA_ROOT", "media"))

# ── Curated product catalog ──
# Each entry: (sku, name, description, price, cost, category, adafruit_pid, image_seq)
# Image URL: https://cdn-shop.adafruit.com/970x728/{pid}-{seq:02d}.jpg
PRODUCTS = [
    # ── Microcontroller Boards ──
    ("AF-4884", "Feather RP2040", "Dual-core RP2040 in Feather form factor, USB-C, 8MB flash", "11.95", "7.17", "Boards", 4884, 4),
    ("AF-2590", "Metro Mini 328 V2", "Arduino-compatible ATmega328P, compact breadboard-friendly", "14.95", "8.97", "Boards", 2590, 0),
    ("AF-3500", "Trinket M0", "Tiny ATSAMD21 board, USB programming, 3.3V logic", "8.95", "5.37", "Boards", 3500, 5),
    ("AF-3405", "HUZZAH32 ESP32 Feather", "ESP32 WiFi+BLE Feather board, 240MHz dual-core", "19.95", "11.97", "Boards", 3405, 0),
    ("AF-2821", "Feather HUZZAH ESP8266", "ESP8266 WiFi Feather, 80MHz, 4MB flash", "14.95", "8.97", "Boards", 2821, 0),
    ("AF-3727", "ItsyBitsy M0 Express", "ATSAMD21 small board, 2MB SPI flash, USB", "11.95", "7.17", "Boards", 3727, 5),
    ("AF-4084", "Grand Central M4 Express", "ATSAMD51 mega board, 70+ I/O pins, SD card", "29.95", "17.97", "Boards", 4084, 3),
    ("AF-3382", "Metro M4 ATSAMD51", "120MHz Cortex M4, Arduino-compatible, 512KB flash", "27.50", "16.50", "Boards", 3382, 5),
    ("AF-2772", "Feather M0 Basic Proto", "ATSAMD21 Cortex M0 Feather with prototyping area", "19.95", "11.97", "Boards", 2772, 0),
    ("AF-4775", "Metro ESP32-S2", "ESP32-S2 WiFi Metro board, USB-C native", "24.95", "14.97", "Boards", 4775, 4),

    # ── Sensors ──
    ("AF-4698", "AS7341 10-Channel Light Sensor", "Visible light sensor with 10 spectral channels, I2C", "18.95", "11.37", "Sensors", 4698, 0),
    ("AF-1782", "MCP9808 Temperature Sensor", "High accuracy I2C temperature sensor, +/-0.25C", "4.95", "2.97", "Sensors", 1782, 0),
    ("AF-2472", "BNO055 9-DOF IMU", "Absolute orientation sensor, sensor fusion built in", "34.95", "20.97", "Sensors", 2472, 0),
    ("AF-5665", "SHT45 Temp & Humidity", "Sensirion high-precision temperature and humidity, I2C", "12.50", "7.50", "Sensors", 5665, 4),
    ("AF-2809", "LIS3DH Accelerometer", "Triple-axis accelerometer, 3.3V or 5V, I2C/SPI", "4.95", "2.97", "Sensors", 2809, 0),
    ("AF-161", "Photo Cell CdS", "CdS photoresistor, light-dependent resistor", "0.95", "0.38", "Sensors", 161, 0),
    ("AF-4566", "AHT20 Temp & Humidity", "Low-cost I2C temperature and humidity sensor", "4.50", "2.70", "Sensors", 4566, 4),
    ("AF-4162", "VEML7700 Lux Sensor", "High accuracy ambient light sensor, I2C, 0-120k lux", "4.95", "2.97", "Sensors", 4162, 0),
    ("AF-4438", "LSM6DSOX 6-DOF IMU", "6-DOF accelerometer and gyroscope, I2C/SPI", "11.95", "7.17", "Sensors", 4438, 0),
    ("AF-3328", "PT100 RTD Amplifier MAX31865", "Precision RTD-to-digital converter, SPI", "14.95", "8.97", "Sensors", 3328, 0),
    ("AF-2167", "IR Break Beam Sensors 3mm", "Infrared break beam sensor pair, 3mm LEDs", "2.95", "1.77", "Sensors", 2167, 0),

    # ── Displays ──
    ("AF-1431", "OLED Breakout 128x64 I2C", "Monochrome 1.3in 128x64 OLED, SH1106 I2C", "19.95", "11.97", "Displays", 1431, 0),
    ("AF-4383", "TFT FeatherWing 3.5in", "3.5in 480x320 TFT display FeatherWing, touch", "29.95", "17.97", "Displays", 4383, 4),
    ("AF-1770", "RGB LED Matrix 16x32", "Medium 16x32 RGB LED matrix panel, 6mm pitch", "24.95", "14.97", "Displays", 1770, 0),
    ("AF-4311", "E-Ink FeatherWing 2.13in", "Tri-color e-paper display, 250x122, red/black/white", "24.95", "14.97", "Displays", 4311, 0),

    # ── Motors & Actuators ──
    ("AF-1438", "Motor/Stepper/Servo Shield v3", "Arduino motor shield, dual H-bridge, servo headers", "19.95", "11.97", "Motors", 1438, 0),
    ("AF-169", "Standard Servo", "Micro servo, 180 degree rotation, 3-wire", "5.95", "3.57", "Motors", 169, 2),
    ("AF-324", "DC Gearbox Motor TT", "3-6V DC gearbox motor, 200RPM, TT shaft", "2.95", "1.77", "Motors", 324, 0),
    ("AF-858", "Stepper Motor NEMA-17", "Bipolar stepper, 200 steps/rev, 12V 350mA", "14.00", "8.40", "Motors", 858, 1),

    # ── Power ──
    ("AF-2011", "PowerBoost 500 Charger", "5V boost converter with LiPoly charger, 500mA", "14.95", "8.97", "Power", 2011, 0),
    ("AF-1578", "LiPoly Battery 3.7V 2500mAh", "Lithium polymer battery, JST connector", "14.95", "8.97", "Power", 1578, 0),
    ("AF-2465", "USB LiPoly Charger v2", "Micro-B USB LiIon/LiPoly charger, 500mA max", "6.95", "4.17", "Power", 2465, 0),
    ("AF-4654", "USB-C PD Sink Breakout", "USB-C PD negotiation breakout, up to 100W", "14.95", "8.97", "Power", 4654, 0),

    # ── Communication ──
    ("AF-2471", "LoRa Radio Feather 900MHz", "RFM95 LoRa radio transceiver Feather, 900MHz", "34.95", "20.97", "Communication", 2471, 0),
    ("AF-4062", "AirLift FeatherWing ESP32", "WiFi co-processor FeatherWing, ESP32 based", "12.95", "7.77", "Communication", 4062, 0),
    ("AF-2633", "Bluefruit LE UART Friend", "Bluetooth LE UART bridge, nRF51822", "17.95", "10.77", "Communication", 2633, 0),

    # ── Prototyping ──
    ("AF-64", "Half-Size Breadboard", "400 tie-point solderless breadboard, white", "5.00", "2.50", "Prototyping", 64, 0),
    ("AF-153", "Jumper Wires M/M 20-pack", "Premium jumper wires, 6in, male-male", "1.95", "0.78", "Prototyping", 153, 2),
    ("AF-1954", "Perma-Proto Half-Size PCB", "Permanent breadboard-layout PCB, 14+ rows", "4.50", "2.70", "Prototyping", 1954, 0),
    ("AF-4631", "STEMMA QT Cable 100mm", "JST SH 4-pin cable, I2C STEMMA QT/Qwiic", "0.95", "0.38", "Prototyping", 4631, 0),

    # ── LEDs & NeoPixels ──
    ("AF-1138", "NeoPixel Ring 16 RGB LED", "WS2812 ring, 16 addressable RGB LEDs", "9.95", "5.97", "LEDs", 1138, 0),
    ("AF-1376", "NeoPixel Stick 8 RGB LED", "WS2812 stick, 8 addressable RGB LEDs", "5.95", "3.57", "LEDs", 1376, 0),
    ("AF-1461", "NeoPixel Strip 1m 60 LED", "WS2812B strip, 60 LEDs/meter, 1 meter", "24.95", "14.97", "LEDs", 1461, 0),
    ("AF-299", "Diffused 5mm LED Pack", "25-pack diffused LEDs, assorted colors", "4.00", "1.60", "LEDs", 299, 0),

    # ── Breakouts & Accessories ──
    ("AF-2264", "MicroSD Card Breakout", "Level-shifting microSD breakout, SPI, 3.3V/5V", "7.50", "4.50", "Accessories", 2264, 5),
    ("AF-254", "MicroSD Card 8GB", "8GB microSD card, class 10, with adapter", "9.95", "5.97", "Accessories", 254, 0),
    ("AF-4399", "STEMMA QT Rotary Encoder", "I2C rotary encoder breakout with NeoPixel", "5.95", "3.57", "Accessories", 4399, 0),
    ("AF-4026", "USB-C Breakout Board", "Simple USB-C connector breakout, all pins", "3.95", "2.37", "Accessories", 4026, 0),
    ("AF-1536", "Analog Joystick", "2-axis analog thumb joystick with select button", "5.95", "3.57", "Accessories", 1536, 0),
    ("AF-3009", "Rotary Trinkey QT2040", "USB rotary encoder with RP2040, NeoPixel", "7.95", "4.77", "Accessories", 3009, 6),
]


def _download_image(pid: int, seq: int) -> bytes | None:
    """Download high-res image from Adafruit CDN. Tries specified seq first, then 00-14."""
    # Try the specified sequence first
    seqs_to_try = [seq] + [s for s in range(15) if s != seq]
    for s in seqs_to_try:
        url = f"https://cdn-shop.adafruit.com/970x728/{pid}-{s:02d}.jpg"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200 and len(resp.content) > 1000:
                return resp.content
        except Exception as e:
            logger.warning(f"Download failed for {url}: {e}")
    return None


def _resize_and_save(image_bytes: bytes, dest_dir: Path) -> dict:
    """Resize to tn/md/hr and save. Returns paths dict."""
    from PIL import Image

    dest_dir.mkdir(parents=True, exist_ok=True)
    paths = {}

    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    # hr — original (already 970x728 from CDN)
    hr_path = dest_dir / "hr.jpg"
    img.save(str(hr_path), "JPEG", quality=90, optimize=True)
    paths["hr"] = str(hr_path.relative_to(MEDIA_ROOT))

    # md — 256px
    md_img = img.copy()
    md_img.thumbnail((256, 256), Image.LANCZOS)
    md_path = dest_dir / "md.jpg"
    md_img.save(str(md_path), "JPEG", quality=85, optimize=True)
    paths["md"] = str(md_path.relative_to(MEDIA_ROOT))

    # tn — 90px
    tn_img = img.copy()
    tn_img.thumbnail((90, 90), Image.LANCZOS)
    tn_path = dest_dir / "tn.jpg"
    tn_img.save(str(tn_path), "JPEG", quality=85, optimize=True)
    paths["tn"] = str(tn_path.relative_to(MEDIA_ROOT))

    return paths


class Command(BaseCommand):
    help = "Seed demo items with real Adafruit products and CC-licensed images"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report without writing")
        parser.add_argument("--clean", action="store_true",
                            help="Remove old HW-* and no-SKU non-service items first")
        parser.add_argument("--images-only", action="store_true",
                            help="Only download images for existing AF-* items missing them")

    def handle(self, *args, **options):
        from apps.products.models import Item

        dry_run = options["dry_run"]
        clean = options["clean"]

        if clean and not dry_run:
            # Deactivate old demo items (can't delete — some have transaction refs)
            hw_count = Item.objects.filter(sku__startswith="HW-").update(
                is_active=False, status="replaced"
            )
            nosku_qs = Item.objects.filter(sku__isnull=True).exclude(
                name__startswith="JPods"
            ).exclude(name__startswith="WCHQ").exclude(name__startswith="Currency").exclude(
                name__startswith="Balance").exclude(name__startswith="Payment").exclude(
                name__startswith="WebClerk")
            nosku_count = nosku_qs.update(is_active=False, status="replaced")
            self.stdout.write(f"  Deactivated: {hw_count} HW-* items, {nosku_count} no-SKU items")

        images_only = options.get("images_only", False)

        created = 0
        skipped = 0
        img_ok = 0
        img_fail = 0

        if images_only:
            return self._download_missing_images(dry_run)

        for sku, name, desc, price, cost, category, pid, seq in PRODUCTS:
            if Item.objects.filter(sku=sku).exists():
                skipped += 1
                if not dry_run:
                    self.stdout.write(f"  SKIP {sku} — already exists")
                continue

            if dry_run:
                self.stdout.write(f"  [DRY RUN] Would create: {sku} — {name} (${price})")
                created += 1
                continue

            item = Item(
                sku=sku,
                name=name,
                description=desc,
                kind="physical",
                uom="EA",
                is_active=True,
                price={
                    "base": price,
                    "retail": price,
                    "msrp": str(round(float(price) * 1.15, 2)),
                    "wholesale": str(round(float(price) * 0.85, 2)),
                    "distributor": str(round(float(price) * 0.75, 2)),
                    "currency": "USD",
                    "history": [],
                    "qty_breaks": [],
                },
                cost={
                    "standard": cost,
                    "last": cost,
                    "avg": cost,
                    "landed": str(round(float(cost) * 1.05, 2)),
                    "currency": "USD",
                    "history": [],
                    "components": {},
                    "qty_breaks": [],
                },
                quantity={
                    "on_hand": 100,
                    "allocated": 0,
                    "available": 100,
                    "on_so": 0,
                    "on_po": 0,
                },
                catalog={
                    "categories": [category],
                    "web": {},
                    "flags": {},
                    "attributes": {},
                },
            )
            item.save()

            # Download and process image
            image_bytes = _download_image(pid, seq)
            if image_bytes:
                try:
                    image_root = MEDIA_ROOT / "images" / "item" / item.ida
                    paths = _resize_and_save(image_bytes, image_root)
                    paths["alt"] = name
                    paths["source"] = f"adafruit:{pid}"

                    # Update metadata.images
                    meta = item.metadata or {}
                    meta["images"] = {
                        "source": f"adafruit:{pid}",
                        "tn": True,
                        "md": True,
                        "hr": True,
                    }
                    Item.objects.filter(pk=item.pk).update(metadata=meta)
                    img_ok += 1
                    self.stdout.write(f"  OK {sku} — {name} (image: {paths['tn']})")
                except Exception as e:
                    img_fail += 1
                    self.stdout.write(self.style.WARNING(f"  OK {sku} — {name} (image resize failed: {e})"))
            else:
                img_fail += 1
                self.stdout.write(self.style.WARNING(f"  OK {sku} — {name} (no image downloaded)"))

            created += 1

        tag = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"\n{tag}Created: {created}, Skipped: {skipped}, "
            f"Images OK: {img_ok}, Images failed: {img_fail}"
        ))

    def _download_missing_images(self, dry_run: bool):
        """Download images for existing AF-* items that don't have them yet."""
        from apps.products.models import Item

        # Build lookup: sku → (pid, seq)
        product_map = {sku: (pid, seq) for sku, _, _, _, _, _, pid, seq in PRODUCTS}

        items = Item.objects.filter(sku__startswith="AF-", is_active=True)
        ok = 0
        fail = 0

        for item in items:
            meta = item.metadata or {}
            images = meta.get("images", {})
            if images.get("tn") is True:
                self.stdout.write(f"  SKIP {item.sku} — already has images")
                continue

            pid_seq = product_map.get(item.sku)
            if not pid_seq:
                self.stdout.write(self.style.WARNING(f"  SKIP {item.sku} — not in product catalog"))
                fail += 1
                continue

            pid, seq = pid_seq
            if dry_run:
                self.stdout.write(f"  [DRY RUN] Would download for {item.sku} (pid={pid})")
                continue

            image_bytes = _download_image(pid, seq)
            if image_bytes:
                try:
                    image_root = MEDIA_ROOT / "images" / "item" / item.ida
                    paths = _resize_and_save(image_bytes, image_root)

                    meta["images"] = {
                        "source": f"adafruit:{pid}",
                        "tn": True,
                        "md": True,
                        "hr": True,
                    }
                    Item.objects.filter(pk=item.pk).update(metadata=meta)
                    ok += 1
                    self.stdout.write(f"  OK {item.sku} — {item.name} (image: {paths['tn']})")
                except Exception as e:
                    fail += 1
                    self.stdout.write(self.style.WARNING(f"  FAIL {item.sku} — resize error: {e}"))
            else:
                fail += 1
                self.stdout.write(self.style.WARNING(f"  FAIL {item.sku} — no image found on CDN"))

        tag = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(f"\n{tag}Images OK: {ok}, Failed: {fail}"))
