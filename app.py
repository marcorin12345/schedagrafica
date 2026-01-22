import streamlit as st
import svgwrite
from PIL import Image
import base64
import io
import json
import random
import os

# Tentativo di importare cairosvg
try:
    import cairosvg
    CAIRO_INSTALLED = True
except Exception:
    CAIRO_INSTALLED = False

# --- SETUP ---
st.set_page_config(layout="wide", page_title="SVG Card Creator Pro")

SAVE_DIR = "esportazioni"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

ICON_PATH_DATA = "M 23.52,7.43 22.31,5.67 20.38,4.42 18.21,4.01 16.03,4.44 14.44,5.42 13.21,6.93 12.5,9.07 12.65,11.18 14.26,11.76 13.91,8.97 14.49,7.48 15.45,6.38 17.36,5.45 19.25,5.47 21.38,6.68 22.57,8.87 22.39,11.33 21.06,13.22 19.19,14.13 16.88,14.2 16.55,13.14 13.66,13.04 12.5,12.67 9.36,9.87 5.38,9.75 4.83,10.25 4.78,11.74 0.63,11.74 0.0,12.36 0.63,13.12 4.75,13.12 4.78,16.59 0.45,16.64 0.03,17.5 0.63,18.0 4.73,18.0 4.81,19.46 5.23,19.96 9.51,19.81 12.68,16.97 16.48,16.62 16.91,15.53 19.75,15.31 21.94,14.15 23.07,12.87 23.85,11.01 23.97,9.32 Z"

def get_img_b64(uploaded_file):
    if not uploaded_file: return None, None, None
    img = Image.open(uploaded_file)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode(), "png", img.size

def create_svg(data_slots, photos, cfg, cable_data, extra_labels):
    dwg = svgwrite.Drawing(size=(1080, 1080))
    dwg.add(dwg.rect(insert=(0, 0), size=('100%', '100%'), fill='white'))

    LEFT_COL_X = 120
    MAIN_PHOTO_RECT = (260, 60, 480, 960) 
    RIGHT_COL_X = 900
    CIRCLE_R = 150

    b64, fmt, size = get_img_b64(photos['f1'])
    if b64:
        ratio = max(MAIN_PHOTO_RECT[2]/size[0], MAIN_PHOTO_RECT[3]/size[1]) * cfg['f1_z']
        w, h = size[0]*ratio, size[1]*ratio
        px = MAIN_PHOTO_RECT[0] + (MAIN_PHOTO_RECT[2]-w)/2 + cfg['f1_x']
        py = MAIN_PHOTO_RECT[1] + (MAIN_PHOTO_RECT[3]-h)/2 + cfg['f1_y']
        clip_f1 = dwg.defs.add(dwg.clipPath(id='clip_f1'))
        clip_f1.add(dwg.rect(insert=(MAIN_PHOTO_RECT[0], MAIN_PHOTO_RECT[1]), size=(MAIN_PHOTO_RECT[2], MAIN_PHOTO_RECT[3])))
        g_main = dwg.g(clip_path="url(#clip_f1)")
        g_main.add(dwg.image(href=f"data:image/{fmt};base64,{b64}", insert=(px, py), size=(w, h)))
        dwg.add(g_main)

    for i, key in enumerate(['f2', 'f3']):
        b64, fmt, size = get_img_b64(photos[key])
        cx, cy = RIGHT_COL_X, 220 + (i * 440)
        if b64:
            clip = dwg.defs.add(dwg.clipPath(id=f'clip_{key}'))
            clip.add(dwg.circle(center=(cx, cy), r=CIRCLE_R))
            ratio = (CIRCLE_R*2 / min(size)) * cfg[f'{key}_z']
            w, h = size[0]*ratio, size[1]*ratio
            ix, iy = cx - w/2 + cfg[f'{key}_x'], cy - h/2 + cfg[f'{key}_y']
            g_extra = dwg.g(clip_path=f"url(#clip_{key})")
            g_extra.add(dwg.image(href=f"data:image/{fmt};base64,{b64}", insert=(ix, iy), size=(w, h)))
            dwg.add(g_extra)
            dwg.add(dwg.circle(center=(cx, cy), r=CIRCLE_R, fill="none", stroke=cfg['text_color'], stroke_width=3))
        
        label_text = extra_labels[i]
        if label_text:
            dwg.add(dwg.text(label_text, insert=(cx, cy + CIRCLE_R + 40), text_anchor="middle", 
                           font_size="22px", fill=cfg['text_color'], font_family="Arial", font_weight="bold"))

    active_items = [d for d in data_slots if d['val'].strip() != ""]
    r_data = 80 * cfg['circle_zoom']
    start_y = 140
    gap = (r_data * 2) + 30
    last_y = start_y
    for i, item in enumerate(active_items[:4]):
        cy = start_y + i * gap
        last_y = cy + r_data
        dwg.add(dwg.circle(center=(LEFT_COL_X, cy), r=r_data, fill=cfg['circle_color']))
        dwg.add(dwg.text(item['val'], insert=(LEFT_COL_X, cy + r_data*0.1), text_anchor="middle", font_weight="bold", 
                       font_size=f"{45*cfg['text_zoom']}px", fill=cfg['text_color'], font_family="Arial"))
        dwg.add(dwg.text(item['unit'], insert=(LEFT_COL_X, cy + r_data*0.5), text_anchor="middle", 
                       font_size=18*cfg['text_zoom'], fill=cfg['text_color'], font_family="Arial"))

    if cable_data['show'] and cable_data['val']:
        c_y = last_y + 80
        g_cbl = dwg.g(transform=f"translate({LEFT_COL_X}, {c_y})")
        g_cbl.add(dwg.path(d=ICON_PATH_DATA, fill=cfg['text_color'], transform="scale(3) translate(-12, -12)"))
        g_cbl.add(dwg.text(cable_data['val'], insert=(0, 65), text_anchor="middle", font_weight="bold", font_size=30, fill=cfg['text_color'], font_family="Arial"))
        g_cbl.add(dwg.text("Lunghezza Cavo", insert=(0, 90), text_anchor="middle", font_size=18, fill=cfg['text_color'], font_family="Arial"))
        dwg.add(g_cbl)

    return dwg.tostring()

# --- INTERFACCIA ---

with st.sidebar:
    st.header("Impostazioni Progetto")
    # MODIFICA NOME PROGETTO
    if 'project_id' not in st.session_state:
        st.session_state['project_id'] = f"Es. 5921{random.randint(1000, 9999)}"
    
    proj_name = st.text_input("Inserisci codice", value=st.session_state['project_id'])
    st.session_state['project_id'] = proj_name

    uploaded_json = st.file_uploader("Carica Progetto (.json)", type=["json"])
    if uploaded_json:
        saved_data = json.load(uploaded_json)
        for k, v in saved_data.items(): st.session_state[k] = v
        st.rerun()

col_input, col_view = st.columns([1, 1], gap="medium")

with col_input:
    with st.expander("Immagini e Testi", expanded=True):
        f1 = st.file_uploader("FOTO 1 (Principale)", type=['jpg', 'jpeg', 'png'])
        f2 = st.file_uploader("FOTO 2 (Alta)", type=['jpg', 'jpeg', 'png'])
        f3 = st.file_uploader("FOTO 3 (Bassa)", type=['jpg', 'jpeg', 'png'])
        lbl2 = st.text_input("Testo sotto Foto 2", key="lbl2")
        lbl3 = st.text_input("Testo sotto Foto 3", key="lbl3")

    with st.expander("Specifiche Tecniche", expanded=True):
        data_slots = []
        for i in range(1, 5):
            c1, c2 = st.columns(2)
            v = c1.text_input(f"Valore {i}", key=f"v{i}")
            u = c2.text_input(f"Etichetta {i}", key=f"u{i}")
            data_slots.append({"val": v, "unit": u})
        show_cbl = st.checkbox("Mostra Icona Cavo", value=True, key="show_cbl")
        cbl_len = st.text_input("Lunghezza Cavo", "120 cm", key="cbl_len")

    with st.expander("Stile"):
        txt_c = st.color_picker("Colore Testo", "#000000", key="txt_c")
        bg_c = st.color_picker("Colore Bolle", "#EFEFEF", key="bg_c")
        t_z = st.slider("Zoom Testo", 0.5, 1.5, 1.0, key="t_z")
        c_z = st.slider("Zoom Bolle", 0.5, 1.2, 1.0, key="c_z")

with col_view:
    st.subheader(f"Anteprima: {st.session_state['project_id']}")
    
    t1, t2, t3 = st.tabs(["Foto 1", "Foto 2", "Foto 3"])
    with t1:
        c1, c2, c3 = st.columns(3); f1x = c1.number_input("X", -500,500,0, key="f1x"); f1y = c2.number_input("Y", -500,500,0, key="f1y"); f1z = c3.slider("Zoom", 0.1, 4.0, 1.0, key="f1z")
    with t2:
        c1, c2, c3 = st.columns(3); f2x = c1.number_input("X ", -500,500,0, key="f2x"); f2y = c2.number_input("Y ", -500,500,0, key="f2y"); f2z = c3.slider("Zoom ", 0.1, 4.0, 1.0, key="f2z")
    with t3:
        c1, c2, c3 = st.columns(3); f3x = c1.number_input("X  ", -500,500,0, key="f3x"); f3y = c2.number_input("Y  ", -500,500,0, key="f3y"); f3z = c3.slider("Zoom  ", 0.1, 4.0, 1.0, key="f3z")

    cfg = {
        "f1_x": f1x, "f1_y": f1y, "f1_z": f1z, "f2_x": f2x, "f2_y": f2y, "f2_z": f2z,
        "f3_x": f3x, "f3_y": f3y, "f3_z": f3z, "text_color": txt_c, "circle_color": bg_c, 
        "text_zoom": t_z, "circle_zoom": c_z
    }

    svg_code = create_svg(data_slots, {'f1':f1, 'f2':f2, 'f3':f3}, cfg, {"show": show_cbl, "val": cbl_len}, [lbl2, lbl3])
    
    # ANTEPRIMA RIDOTTA (width=400 invece che container_width)
    st.image(svg_code, width=450)

    st.divider()
    c_d1, c_d2, c_d3 = st.columns(3)
    
    c_d1.download_button("SVG", svg_code, f"{st.session_state['project_id']}.svg", "image/svg+xml")
    
    current_state = {**cfg, "lbl2": lbl2, "lbl3": lbl3, "show_cbl": show_cbl, "cbl_len": cbl_len, "project_id": st.session_state['project_id']}
    for i in range(4):
        current_state[f"v{i+1}"] = data_slots[i]['val']
        current_state[f"u{i+1}"] = data_slots[i]['unit']
    
    json_data = json.dumps(current_state, indent=4)
    c_d2.download_button("JSON", json_data, f"{st.session_state['project_id']}.json", "application/json")

    if CAIRO_INSTALLED:
        try:
            png_img = cairosvg.svg2png(bytestring=svg_code.encode('utf-8'), output_width=1080, output_height=1080)
            final_jpg = Image.open(io.BytesIO(png_img)).convert("RGB")
            buf = io.BytesIO()
            final_jpg.save(buf, format="JPEG", quality=95)
            c_d3.download_button("JPG", buf.getvalue(), f"{st.session_state['project_id']}.jpg", "image/jpeg")
        except Exception as e:
            st.error(f"Errore Cairo: {e}")
    else:
        st.warning("JPG disabilitato. Vedi istruzioni Cairo.")
