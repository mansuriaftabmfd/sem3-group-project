from PIL import Image, ImageDraw, ImageFont
import os
import math
from datetime import datetime
import hashlib
import qrcode

# ── SECURITY ─────────────────────────────────────────────────────
SECRET_KEY = "SKILLVERSE_PRIVATE_KEY_2026"

# ── Canvas: A4 Landscape @ 300 DPI ───────────────────────────────
W, H = 2480, 1754

# ── Palette ──────────────────────────────────────────────────────
NAVY        = (8,   18,  36)
NAVY_LIGHT  = (14,  28,  54)
NAVY_DARK   = (4,   10,  22)
NAVY_MID    = (10,  22,  44)
GOLD        = (212, 175, 55)
GOLD_LIGHT  = (245, 222, 160)
GOLD_DIM    = (170, 140, 60)
GOLD_FAINT  = (100, 84,  36)
WHITE       = (245, 245, 245)
SILVER      = (210, 210, 210)

# ── Font directory ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Fonts are in FRONTEND/static/fonts, go up to project root then to FRONTEND
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
FONT_DIR = os.path.join(PROJECT_ROOT, "FRONTEND", "static", "fonts")

def _font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)

# ── Text helpers ──────────────────────────────────────────────────
def _tw(draw, text, font):
    return draw.textlength(text, font=font)

def _cx(draw, text, y, font, fill):
    w = _tw(draw, text, font)
    draw.text(((W - w) // 2, y), text, font=font, fill=fill)

def _cx_at(draw, text, y, font, fill, cx):
    w = _tw(draw, text, font)
    draw.text((int(cx - w // 2), y), text, font=font, fill=fill)

# ── Shape helpers ─────────────────────────────────────────────────
def _diamond(draw, cx, cy, r, fill):
    draw.polygon([(cx, cy-r),(cx+r, cy),(cx, cy+r),(cx-r, cy)], fill=fill)

def _rule_with_diamond(draw, y, margin, color_line, color_diamond, d=10):
    draw.line([(margin, y),(W//2 - d*2, y)], fill=color_line, width=1)
    draw.line([(W//2 + d*2, y),(W-margin, y)], fill=color_line, width=1)
    _diamond(draw, W//2, y, d, color_diamond)

def _corner_ornament(draw, cx, cy, size, angle_deg):
    angle = math.radians(angle_deg)
    d = size // 2
    def rot(x, y):
        return (cx + x*math.cos(angle) - y*math.sin(angle),
                cy + x*math.sin(angle) + y*math.cos(angle))
    pts = [rot(0,-d), rot(d*0.55,0), rot(0,d), rot(-d*0.55,0)]
    draw.polygon(pts, fill=GOLD)
    for dx, dy in [(0, d*2.0),(0,-d*2.0),(d*2.0,0),(-d*2.0,0)]:
        draw.line([rot(dx*0.55, dy*0.55), rot(dx, dy)], fill=GOLD_DIM, width=3)

def _medal(draw, cx, cy, r):
    draw.ellipse([cx-r,cy-r,cx+r,cy+r], outline=GOLD, width=6)
    ri = int(r * 0.82)
    draw.ellipse([cx-ri,cy-ri,cx+ri,cy+ri], outline=GOLD_DIM, width=2)
    for i in range(36):
        a = math.radians(i * 10)
        x1,y1 = cx + r*0.88*math.cos(a), cy + r*0.88*math.sin(a)
        x2,y2 = cx + r*0.97*math.cos(a), cy + r*0.97*math.sin(a)
        draw.line([(x1,y1),(x2,y2)], fill=GOLD_DIM, width=2)
    for i in range(8):
        a = math.radians(i * 45)
        draw.line([(cx, cy),
                   (cx + ri*0.50*math.cos(a), cy + ri*0.50*math.sin(a))],
                  fill=GOLD, width=4)
    draw.ellipse([cx-13,cy-13,cx+13,cy+13], fill=GOLD)

def _squiggle_signature(draw, cx, y):
    offsets = [(-90, 0, GOLD_LIGHT), (-70, 8, GOLD_DIM), (-50,-6, GOLD_LIGHT)]
    for x0, dy, col in offsets:
        pts = []
        for i in range(12):
            px = cx + x0 + i*16
            py = y + dy + (6 if i%2==0 else -6)
            pts.append((px, py))
        draw.line(pts, fill=col, width=3, joint="curve")

def _gradient_bg(img):
    pix = img.load()
    for dy in range(H):
        t   = dy / (H - 1)
        col = (int(NAVY_LIGHT[0] + (NAVY_DARK[0] - NAVY_LIGHT[0]) * t),
               int(NAVY_LIGHT[1] + (NAVY_DARK[1] - NAVY_LIGHT[1]) * t),
               int(NAVY_LIGHT[2] + (NAVY_DARK[2] - NAVY_LIGHT[2]) * t))
        for dx in range(W):
            pix[dx, dy] = col

# ── Hash ──────────────────────────────────────────────────────────
def generate_hash(student, skill, cert_id, order_id):
    raw = f"{student}{skill}{cert_id}{order_id}{SECRET_KEY}"
    return hashlib.sha256(raw.encode()).hexdigest()


# ═════════════════════════════════════════════════════════════════
# DRAW CERTIFICATE
# Layout zones (H=1754px):
#   Zone 1 – Header block  :  80 –  790
#   Zone 2 – Info row      : 800 –  960
#   Zone 3 – Signatures    : 970 – 1200
#   Zone 4 – Bottom strip  :1220 – 1660  (band + QR)
#   Zone 5 – Hash footer   :1670 – 1710
# ═════════════════════════════════════════════════════════════════
def draw_certificate(student_name, skill_name,
                     provider_name="SkillVerse",
                     order_id="SV-ORDER-001",
                     cert_id="CERT-XXXX",
                     completion_date=None):

    if completion_date is None:
        completion_date = datetime.now().strftime("%d %B %Y")

    cert_hash  = generate_hash(student_name, skill_name, cert_id, order_id)
    verify_url = f"https://skillverse-oh9z.onrender.com/verify/{cert_id}"

    QR = 240
    qr_img = qrcode.make(verify_url).resize((QR, QR))

    img = Image.new("RGB", (W, H), NAVY)
    _gradient_bg(img)
    draw = ImageDraw.Draw(img)

    # Gold side bars
    BAR = 22
    for x in range(BAR):
        t   = x / BAR
        col = (int(GOLD[0]*(1-t) + GOLD_DIM[0]*t),
               int(GOLD[1]*(1-t) + GOLD_DIM[1]*t),
               int(GOLD[2]*(1-t) + GOLD_DIM[2]*t))
        draw.line([(x,0),(x,H)],       fill=col)
        draw.line([(W-1-x,0),(W-1-x,H)], fill=col)

    # Double border
    m = 58
    draw.rectangle([m,   m,   W-m,   H-m  ], outline=GOLD,    width=5)
    draw.rectangle([m+16,m+16,W-m-16,H-m-16], outline=GOLD_DIM, width=1)

    # Corner ornaments
    off = m + 2
    for cx_, cy_, ang in [(off,off,45),(W-off,off,135),
                          (W-off,H-off,225),(off,H-off,315)]:
        _corner_ornament(draw, cx_, cy_, 30, ang)

    # Fonts
    f_brand   = _font("Montserrat-SemiBold.ttf",       28)
    f_title   = _font("PlayfairDisplay-Bold.ttf",       78)
    f_sub     = _font("CormorantGaramond-Regular.ttf",  36)
    f_name    = _font("PlayfairDisplay-Bold.ttf",       108)
    f_skill   = _font("Montserrat-SemiBold.ttf",        50)
    f_prov    = _font("Montserrat-SemiBold.ttf",        34)
    f_label   = _font("Montserrat-SemiBold.ttf",        21)
    f_val     = _font("Montserrat-SemiBold.ttf",        27)
    f_signame = _font("Montserrat-SemiBold.ttf",        25)
    f_sigrole = _font("Montserrat-SemiBold.ttf",        19)
    f_script  = _font("GreatVibes-Regular.ttf",         62)
    f_tiny    = _font("Montserrat-Regular.ttf",         18)

    # ════════════════════════════════════════════════════════
    # ZONE 1 – HEADER
    # ════════════════════════════════════════════════════════

    _rule_with_diamond(draw, 118, m+40, GOLD_DIM, GOLD, d=12)
    _cx(draw, "S K I L L V E R S E", 140, f_brand, GOLD)
    _cx(draw, "Certificate of Completion", 188, f_title, WHITE)
    draw.line([(W//2-400, 292),(W//2+400, 292)], fill=GOLD_DIM, width=1)
    _cx(draw, "This certificate is proudly presented to", 312, f_sub, SILVER)

    # Student name with emboss shadow
    nw = int(_tw(draw, student_name, f_name))
    nx = (W - nw) // 2
    for ox, oy in [(-2,3),(2,3),(0,4)]:
        draw.text((nx+ox, 368+oy), student_name, font=f_name, fill=GOLD_DIM)
    _cx(draw, student_name, 368, f_name, GOLD_LIGHT)

    # Ornamental divider under name — y=548, ~72px below name baseline
    ndiv = 548
    draw.line([(m+60,    ndiv),(W//2-84, ndiv)], fill=GOLD_DIM,   width=2)
    draw.line([(W//2+84, ndiv),(W-m-60,  ndiv)], fill=GOLD_DIM,   width=2)
    draw.line([(m+60,    ndiv+7),(W//2-84, ndiv+7)], fill=GOLD_FAINT, width=1)
    draw.line([(W//2+84, ndiv+7),(W-m-60,  ndiv+7)], fill=GOLD_FAINT, width=1)
    _diamond(draw, W//2,      ndiv+3, 16, GOLD)
    _diamond(draw, W//2-56,   ndiv+3,  7, GOLD_DIM)
    _diamond(draw, W//2+56,   ndiv+3,  7, GOLD_DIM)
    _diamond(draw, W//2-102,  ndiv+3,  4, GOLD_FAINT)
    _diamond(draw, W//2+102,  ndiv+3,  4, GOLD_FAINT)

    _cx(draw, "for successfully completing", 578, f_sub, SILVER)

    # Skill pill
    sk_w = int(_tw(draw, skill_name, f_skill))
    pp   = 48
    px0, py0 = (W - sk_w)//2 - pp, 626
    px1, py1 = (W + sk_w)//2 + pp, 698
    draw.rounded_rectangle([px0,py0,px1,py1], radius=12,
                            fill=NAVY_MID, outline=GOLD_DIM, width=1)
    _cx(draw, skill_name, 634, f_skill, GOLD)

    _cx(draw, "A freelancing certification program offered by", 720, f_sub, SILVER)
    _cx(draw, provider_name, 766, f_prov, GOLD_LIGHT)

    # ════════════════════════════════════════════════════════
    # ZONE 2 – INFO ROW
    # ════════════════════════════════════════════════════════

    _rule_with_diamond(draw, 840, m+40, GOLD_DIM, GOLD_DIM, d=9)

    info_y = 870
    c1, c2, c3 = W//4, W//2, 3*W//4

    _cx_at(draw, "ORDER ID",       info_y,      f_label, GOLD_DIM, c1)
    _cx_at(draw, "DATE ISSUED",    info_y,      f_label, GOLD_DIM, c2)
    _cx_at(draw, "CERTIFICATE ID", info_y,      f_label, GOLD_DIM, c3)

    _cx_at(draw, f"#{order_id}",  info_y + 38, f_val, WHITE, c1)
    _cx_at(draw, completion_date, info_y + 38, f_val, WHITE, c2)
    _cx_at(draw, cert_id,         info_y + 38, f_val, WHITE, c3)

    for vx in [W//4 + W//8, W//2 + W//8]:
        draw.line([(vx, info_y-6),(vx, info_y+78)], fill=GOLD_FAINT, width=1)

    _rule_with_diamond(draw, 1010, m+40, GOLD_DIM, GOLD_DIM, d=9)

    # ════════════════════════════════════════════════════════
    # ZONE 3 – SIGNATURES
    # ════════════════════════════════════════════════════════

    s1, s2   = W//3, 2*W//3
    script_y = 1035
    line_y   = 1148
    name_y   = 1160
    role_y   = 1192

    # Left – Aftab
    sig_txt = "Aftab"
    sw  = int(_tw(draw, sig_txt, f_script))
    sx  = s1 - sw//2
    for ox,oy in [(-1,2),(1,2),(0,3)]:
        draw.text((sx+ox, script_y+oy), sig_txt, font=f_script, fill=GOLD_DIM)
    draw.text((sx, script_y), sig_txt, font=f_script, fill=GOLD_LIGHT)
    draw.line([(s1-190, line_y),(s1+190, line_y)], fill=GOLD_DIM, width=1)
    _cx_at(draw, "Aftab",                  name_y, f_signame, WHITE,    s1)
    _cx_at(draw, "Founder & Director, SkillVerse",  role_y, f_sigrole, GOLD_DIM, s1)

    # Centre – medal
    _medal(draw, W//2, line_y - 18, 88)

    # Right – Mayur Purohit script signature
    sig_txt2 = "Mayur Purohit"
    sw2 = int(_tw(draw, sig_txt2, f_script))
    sx2 = s2 - sw2 // 2
    for ox, oy in [(-1, 2), (1, 2), (0, 3)]:
        draw.text((sx2+ox, script_y+oy), sig_txt2, font=f_script, fill=GOLD_DIM)
    draw.text((sx2, script_y), sig_txt2, font=f_script, fill=GOLD_LIGHT)
    draw.line([(s2-190, line_y),(s2+190, line_y)], fill=GOLD_DIM, width=1)
    _cx_at(draw, "Mayur Purohit",          name_y, f_signame, WHITE,    s2)
    _cx_at(draw, "Authorized Signature",   role_y, f_sigrole, GOLD_DIM, s2)

    # ════════════════════════════════════════════════════════
    # ZONE 4 – BOTTOM DECORATIVE STRIP + QR
    # ════════════════════════════════════════════════════════

    _rule_with_diamond(draw, 1260, m+40, GOLD_DIM, GOLD_DIM, d=9)

    # Accent band
    band_y, band_h = 1280, 56
    draw.rectangle([m+18, band_y, W-m-18, band_y+band_h],
                   fill=(10, 20, 42), outline=GOLD_FAINT, width=1)

    # Diamond track — left and right thirds only
    step = 90
    for bx in range(m+60, W//2 - 500, step):
        _diamond(draw, bx, band_y + band_h//2, 6, GOLD_FAINT)
        draw.line([(bx+8, band_y+band_h//2),(bx+step-8, band_y+band_h//2)],
                  fill=GOLD_FAINT, width=1)
    for bx in range(W//2 + 500, W-m-40, step):
        _diamond(draw, bx, band_y + band_h//2, 6, GOLD_FAINT)
        draw.line([(bx+8, band_y+band_h//2),(bx+step-8, band_y+band_h//2)],
                  fill=GOLD_FAINT, width=1)

    # Band centre text — clean, no overlap
    band_txt = "SkillVerse Certified Achievement  ·  Certificate of Excellence  ·  Verified & Authenticated"
    _cx(draw, band_txt, band_y + 18, f_tiny, GOLD_DIM)

    # "Scan to verify" label
    _cx(draw, "— Scan QR Code to Verify Certificate Authenticity —",
        1366, f_label, GOLD_DIM)

    # QR centred
    qr_x = W//2 - QR//2
    qr_y = 1406
    pad  = 10
    draw.rectangle([qr_x-pad, qr_y-pad, qr_x+QR+pad, qr_y+QR+pad], fill=WHITE)
    img.paste(qr_img, (qr_x, qr_y))

    # Rule below QR
    _rule_with_diamond(draw, qr_y + QR + pad + 28, m+40,
                       GOLD_FAINT, GOLD_FAINT, d=7)

    # ════════════════════════════════════════════════════════
    # ZONE 5 – HASH FOOTER
    # ════════════════════════════════════════════════════════
    hash_y = qr_y + QR + pad + 50
    _cx(draw, f"Verification Hash:  {cert_hash[:52]}...", hash_y, f_tiny, GOLD_FAINT)

    return img


# ── Public API ────────────────────────────────────────────────────

def generate_cert_id():
    """Return a unique cert ID like CERT-A1B2C3D4."""
    import uuid
    return f"CERT-{uuid.uuid4().hex[:8].upper()}"


def generate_certificate(student_name, skill_name,
                         provider_name="SkillVerse",
                         order_id="SV-ORDER-001",
                         cert_id=None,
                         template_path=None,
                         completion_date=None):
    """
    Generate a certificate PDF and return its absolute path.
    Saved to static/certificates/<cert_id>.pdf
    """
    if cert_id is None:
        cert_id = generate_cert_id()
    if completion_date is None:
        completion_date = datetime.now().strftime("%d %B %Y")

    # Save to FRONTEND/static/certificates/ which is where Flask's static_folder points.
    # PROJECT_ROOT is already computed at module level (BACKEND/services → up 2 → project root)
    output_dir = os.path.join(PROJECT_ROOT, "FRONTEND", "static", "certificates")
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{cert_id}.pdf")

    img = draw_certificate(
        student_name    = student_name,
        skill_name      = skill_name,
        provider_name   = provider_name,
        order_id        = str(order_id),
        cert_id         = cert_id,
        completion_date = completion_date,
    )
    img.save(output_path, "PDF", resolution=300)
    return output_path


# ── Test (run directly to preview) ───────────────────────────────
if __name__ == "__main__":
    cert = draw_certificate(
        student_name = "John Doe",
        skill_name   = "Python Programming",
        order_id     = "SV-2026-001",
        cert_id      = "CERT-9E9077"
    )
    cert.save("skillverse_certificate_verified.png")
    print("✅ Certificate generated: skillverse_certificate_verified.png")