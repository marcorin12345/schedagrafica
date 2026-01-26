import streamlit as st
import svgwrite
from PIL import Image
import base64
import io
import json
import random
import re

# Tentativo di importare cairosvg
try:
    import cairosvg
    CAIRO_INSTALLED = True
except Exception:
    CAIRO_INSTALLED = False

# --- SETUP ---
st.set_page_config(layout="wide", page_title="SVG Card Creator Pro")

st.markdown("""
    <style>
        [data-testid="column"]:nth-child(2) [data-testid="stVerticalBlock"] {
            position: sticky;
            top: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

ICON_PATH_DATA = "M 23.52,7.43 22.31,5.67 20.38,4.42 18.21,4.01 16.03,4.44 14.44,5.42 13.21,6.93 12.5,9.07 12.65,11.18 14.26,11.76 13.91,8.97 14.49,7.48 15.45,6.38 17.36,5.45 19.25,5.47 21.38,6.68 22.57,8.87 22.39,11.33 21.06,13.22 19.19,14.13 16.88,14.2 16.55,13.14 13.66,13.04 12.5,12.67 9.36,9.87 5.38,9.75 4.83,10.25 4.78,11.74 0.63,11.74 0.0,12.36 0.63,13.12 4.75,13.12 4.78,16.59 0.45,16.64 0.03,17.5 0.63,18.0 4.73,18.0 4.81,19.46 5.23,19.96 9.51,19.81 12.68,16.97 16.48,16.62 16.91,15.53 19.75,15.31 21.94,14.15 23.07,12.87 23.85,11.01 23.85,11.01 23.97,9.32 Z"

# Regex per identificare unità di misura comuni
UNIT_REGEX = r"^(.*?)(Kg|kg|cm|mm|L|l|Ø|ml|V|W|Ah|Ah|Hz|h|min|s|bar|psi|g|m|km|V|A|m²|m³)$"

def get_img_b64(uploaded_file):
    if not uploaded_file: return None, None, None
    try:
        img = Image.open(uploaded_file)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode(), "png", img.size
    except: return None, None, None

def draw_photo_rect(dwg, photo_file, rect, cfg, key):
    b64, fmt, size = get_img_b64(photo_file)
    if b64:
        rx, ry, rw, rh = rect
        ratio = max(rw/size[0], rh/size[1]) * cfg[f'{key}_z']
        w, h = size[0]*ratio, size[1]*ratio
        px = rx + (rw-w)/2 + cfg[f'{key}_x']
        py = ry + (rh-h)/2 + cfg[f'{key}_y']
        clip = dwg.defs.add(dwg.clipPath(id=f'clip_{key}'))
        clip.add(dwg.rect(insert=(rx, ry), size=(rw, rh)))
        g = dwg.g(clip_path=f"url(#clip_{key})")
        g.add(dwg.image(href=f"data:image/{fmt};base64,{b64}", insert=(px, py), size=(w, h)))
        dwg.add(g)

def draw_photo_circle(dwg, photo_file, center, r, cfg, key, label=""):
    b64, fmt, size = get_img_b64(photo_file)
    cx, cy = center
    if b64:
        clip = dwg.defs.add(dwg.clipPath(id=f'clip_{key}'))
        clip.add(dwg.circle(center=(cx, cy), r=r))
        ratio = (r*2 / min(size)) * cfg[f'{key}_z']
        w, h = size[0]*ratio, size[1]*ratio
        ix, iy = cx - w/2 + cfg[f'{key}_x'], cy - h/2 + cfg[f'{key}_y']
        g = dwg.g(clip_path=f"url(#clip_{key})")
        g.add(dwg.image(href=f"data:image/{fmt};base64,{b64}", insert=(ix, iy), size=(w, h)))
        dwg.add(g)
        dwg.add(dwg.circle(center=(cx, cy), r=r, fill="none", stroke=cfg['text_color'], stroke_width=3, stroke_dasharray="10,10"))
    
    if label:
        l_lines = [l for l in label.split('\n') if l.strip()]
        l_size = 22 * cfg['unit_zoom']
        curr_ly = cy + r + 35
        for line in l_lines:
            dwg.add(dwg.text(line, insert=(cx, curr_ly), text_anchor="middle", 
                           font_size=f"{l_size}px", fill=cfg['label_color'], font_family="Arial", font_weight="bold"))
            curr_ly += l_size * cfg['line_spacing']

def draw_spec_circles(dwg, data_slots, points, cfg):
    r_data = 80 * cfg['circle_zoom']
    ls = cfg.get('line_spacing', 1.1)
    active_items = [d for d in data_slots if d['val'].strip() != "" or d['unit'].strip() != ""]
    
    for i, item in enumerate(active_items[:len(points)]):
        cx, cy = points[i]
        dwg.add(dwg.circle(center=(cx, cy), r=r_data, fill=cfg['circle_color']))
        
        v_lines = [l for l in item['val'].split('\n') if l.strip()]
        u_lines = [l for l in item['unit'].split('\n') if l.strip()]
        
        v_size = 45 * cfg['val_zoom']
        u_size = 18 * cfg['unit_zoom']
        
        v_h = len(v_lines) * v_size * ls
        u_h = len(u_lines) * u_size * ls
        total_h = v_h + u_h
        curr_y = cy - (total_h / 2) + (v_size * 0.8)

        # Rendering VALORI con gestione unità piccole
        for line in v_lines:
            match = re.match(UNIT_REGEX, line.strip())
            if match:
                main_txt, unit_txt = match.groups()
                # Creiamo un elemento testo che contiene due span di diversa dimensione
                text_elem = dwg.text("", insert=(cx, curr_y), text_anchor="middle", 
                                     font_weight="bold", font_size=f"{v_size}px", 
                                     fill=cfg['text_color'], font_family="Arial")
                text_elem.add(dwg.tspan(main_txt))
                text_elem.add(dwg.tspan(unit_txt, font_size=f"{v_size * 0.6}px")) # Unità al 60%
                dwg.add(text_elem)
            else:
                dwg.add(dwg.text(line, insert=(cx, curr_y), text_anchor="middle", 
                               font_weight="bold", font_size=f"{v_size}px", 
                               fill=cfg['text_color'], font_family="Arial"))
            curr_y += v_size * ls
        
        # Rendering ETICHETTE (sotto il valore)
        for line in u_lines:
            dwg.add(dwg.text(line, insert=(cx, curr_y), text_anchor="middle", 
                           font_size=f"{u_size}px", fill=cfg['label_color'], font_family="Arial"))
            curr_y += u_size * ls

def create_svg(model, data_slots, photos, cfg, cable_data, extra_labels):
    dwg = svgwrite.Drawing(size=(1080, 1080))
    dwg.add(dwg.rect(insert=(0, 0), size=('100%', '100%'), fill='white'))
    
    spec_points = []
    cp_x, cp_y = 120, 900

    if model == "A (Elettrico)":
        draw_photo_rect(dwg, photos['f1'], (260, 60, 480, 960), cfg, 'f1')
        spec_points = [(120, 140 + i*195) for i in range(4)]
        cp_x, cp_y = 120, 900
    elif model == "B":
        draw_photo_rect(dwg, photos['f1'], (80, 60, 550, 750), cfg, 'f1')
        spec_points = [(150 + i*210, 930) for i in range(4)]
        cp_x, cp_y = 930, 910
    elif model == "C":
        draw_photo_rect(dwg, photos['f1'], (80, 260, 550, 750), cfg, 'f1')
        spec_points = [(150 + i*210, 130) for i in range(4)]
        cp_x, cp_y = 930, 130
    elif model == "D":
        draw_photo_rect(dwg, photos['f1'], (400, 60, 600, 750), cfg, 'f1')
        spec_points = [(150 + i*210, 930) for i in range(4)]
        cp_x, cp_y = 930, 910
    elif model == "E":
        draw_photo_rect(dwg, photos['f1'], (60, 100, 460, 700), cfg, 'f1')
        draw_photo_rect(dwg, photos['f2'], (560, 100, 460, 700), cfg, 'f2')
        spec_points = [(150 + i*210, 930) for i in range(4)]
        cp_x, cp_y = 930, 910
    elif model == "F":
        draw_photo_rect(dwg, photos['f1'], (140, 60, 800, 750), cfg, 'f1')
        spec_points = [(150 + i*210, 930) for i in range(4)]
        cp_x, cp_y = 930, 910

    if model != "E":
        draw_photo_circle(dwg, photos['f2'], (cfg['f2_bx'], cfg['f2_by']), cfg['f2_br'], cfg, 'f2', extra_labels[0])
    draw_photo_circle(dwg, photos['f3'], (cfg['f3_bx'], cfg['f3_by']), cfg['f3_br'], cfg, 'f3', extra_labels[1])

    draw_spec_circles(dwg, data_slots, spec_points, cfg)
    
    if cable_data['show'] and cable_data['val']:
        g_cbl = dwg.g(transform=f"translate({cp_x}, {cp_y})")
        g_cbl.add(dwg.path(d=ICON_PATH_DATA, fill=cfg['text_color'], transform="scale(2.5) translate(-12, -12)"))
        g_cbl.add(dwg.text(cable_data['val'], insert=(0, 55), text_anchor="middle", font_weight="bold", font_size=24, fill=cfg['text_color'], font_family="Arial"))
        dwg.add(g_cbl)

    return dwg.tostring()

# --- INTERFACCIA ---

with st.sidebar:
    st.header("⚙️ Progetto")
    model_type = st.selectbox("Seleziona Modello", ["A (Elettrico)", "B", "C", "D", "E", "F"])
    
    if 'project_id' not in st.session_state:
        st.session_state['project_id'] = f"{random.randint(1000, 9999)}"
    proj_name = st.text_input("Codice Progetto", value=st.session_state['project_id'])
    
    uploaded_json = st.file_uploader("Carica Progetto (.json)", type=["json"])
    if uploaded_json:
        saved_data = json.load(uploaded_json)
        for k, v in saved_data.items(): st.session_state[k] = v
        st.rerun()

col_input, col_view = st.columns([1, 1], gap="medium")

with col_input:
    with st.expander("🖼️ Immagini e Testi", expanded=True):
        f1 = st.file_uploader("FOTO 1 (Principale)", type=['jpg', 'jpeg', 'png'])
        f2 = st.file_uploader("FOTO 2", type=['jpg', 'jpeg', 'png'])
        f3 = st.file_uploader("FOTO 3", type=['jpg', 'jpeg', 'png'])
        lbl2 = st.text_area("Etichetta Foto 2", key="lbl2", height=80)
        lbl3 = st.text_area("Etichetta Foto 3", key="lbl3", height=80)

    with st.expander("📊 Specifiche Tecniche", expanded=True):
        data_slots = []
        for i in range(1, 5):
            c1, c2 = st.columns(2)
            v = c1.text_area(f"Valore {i}", key=f"v{i}", height=65, help="Esempio: 50 Kg. L'unità sarà rimpicciolita.")
            u = c2.text_area(f"Etichetta {i}", key=f"u{i}", height=65)
            data_slots.append({"val": v, "unit": u})
        show_cbl = st.checkbox("Mostra Icona Cavo", value=True, key="show_cbl")
        cbl_len = st.text_input("Lunghezza Cavo", "120 cm", key="cbl_len")

    with st.expander("🎨 Stile Avanzato"):
        c_txt, c_lbl = st.columns(2)
        txt_c = c_txt.color_picker("Colore Valori", "#000000", key="txt_c")
        lbl_c = c_lbl.color_picker("Colore Etichette", "#333333", key="lbl_c")
        bg_c = st.color_picker("Colore Bolle", "#EFEFEF", key="bg_c")
        
        s1, s2 = st.columns(2)
        v_z = s1.slider("Zoom Valori", 0.5, 2.0, 1.0)
        u_z = s2.slider("Zoom Etichette", 0.5, 2.0, 1.0)
        
        c_z = st.slider("Dimensione Bolle Info", 0.5, 1.5, 1.0)
        l_s = st.slider("Interlinea (Line Spacing)", 0.5, 2.5, 1.1, step=0.1)

with col_view:
    st.subheader(f"Anteprima: {model_type}")
    
    # Valori di default
    def_f2x, def_f2y, def_f3x, def_f3y = 900, 220, 900, 660
    if model_type == "C": def_f2x, def_f2y, def_f3x, def_f3y = 900, 480, 900, 880
    if model_type == "D": def_f2x, def_f2y, def_f3x, def_f3y = 180, 220, 180, 660

    tabs = st.tabs(["Foto 1", "Box Foto 2", "Box Foto 3"])
    
    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        f1x = c1.number_input("Sposta X", -1000, 1000, 0, key="f1x_v")
        f1y = c2.number_input("Sposta Y", -1000, 1000, 0, key="f1y_v")
        f1z = c3.slider("Zoom Foto", 0.1, 5.0, 1.0, key="f1z_v")
        
    with tabs[1]:
        bc1, bc2, bc3 = st.columns(3)
        f2bx = bc1.number_input("Box X", 0, 1080, def_f2x)
        f2by = bc2.number_input("Box Y", 0, 1080, def_f2y)
        f2br = bc3.number_input("Raggio Cerchio", 10, 500, 150)
        ic1, ic2, ic3 = st.columns(3)
        f2x = ic1.number_input("Foto X", -1000, 1000, 0, key="f2x_v")
        f2y = ic2.number_input("Foto Y", -1000, 1000, 0, key="f2y_v")
        f2z = ic3.slider("Zoom Foto", 0.1, 5.0, 1.0, key="f2z_v")

    with tabs[2]:
        bc1, bc2, bc3 = st.columns(3)
        f3bx = bc1.number_input("Box X ", 0, 1080, def_f3x)
        f3by = bc2.number_input("Box Y ", 0, 1080, def_f3y)
        f3br = bc3.number_input("Raggio Cerchio ", 10, 500, 150)
        ic1, ic2, ic3 = st.columns(3)
        f3x = ic1.number_input("Foto X ", -1000, 1000, 0, key="f3x_v")
        f3y = ic2.number_input("Foto Y ", -1000, 1000, 0, key="f3y_v")
        f3z = ic3.slider("Zoom Foto ", 0.1, 5.0, 1.0, key="f3z_v")

    cfg = {
        "f1_x": f1x, "f1_y": f1y, "f1_z": f1z,
        "f2_x": f2x, "f2_y": f2y, "f2_z": f2z, "f2_bx": f2bx, "f2_by": f2by, "f2_br": f2br,
        "f3_x": f3x, "f3_y": f3y, "f3_z": f3z, "f3_bx": f3bx, "f3_by": f3by, "f3_br": f3br,
        "text_color": txt_c, "label_color": lbl_c, "circle_color": bg_c,
        "val_zoom": v_z, "unit_zoom": u_z, "circle_zoom": c_z, "line_spacing": l_s
    }

    svg_code = create_svg(model_type, data_slots, {'f1':f1, 'f2':f2, 'f3':f3}, cfg, {"show": show_cbl, "val": cbl_len}, [lbl2, lbl3])
    st.image(svg_code, use_container_width=True)

    st.divider()
    c_d1, c_d2, c_d3 = st.columns(3)
    c_d1.download_button("💾 SVG", svg_code, f"{st.session_state['project_id']}.svg", "image/svg+xml")
    current_state = {**cfg, "model_type": model_type, "lbl2": lbl2, "lbl3": lbl3, "show_cbl": show_cbl, "cbl_len": cbl_len, "project_id": st.session_state['project_id']}
    for i in range(4):
        current_state[f"v{i+1}"] = data_slots[i]['val']; current_state[f"u{i+1}"] = data_slots[i]['unit']
    c_d2.download_button("📥 JSON", json.dumps(current_state, indent=4), f"{st.session_state['project_id']}.json", "application/json")

    if CAIRO_INSTALLED:
        try:
            png_img = cairosvg.svg2png(bytestring=svg_code.encode('utf-8'), output_width=1080, output_height=1080)
            buf = io.BytesIO(); Image.open(io.BytesIO(png_img)).convert("RGB").save(buf, format="JPEG", quality=95)
            c_d3.download_button("🖼️ JPG", buf.getvalue(), f"{st.session_state['project_id']}.jpg", "image/jpeg")
        except Exception as e: st.error(f"Errore JPG: {e}")