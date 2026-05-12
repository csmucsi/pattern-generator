import streamlit as st
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- Helper Functions for Symmetry & Interlocking ---

def get_layout_signature(layout):
    """Creates a set of coordinates to easily compare if two layouts are identical."""
    # We round to 1 decimal place to avoid floating point precision errors
    return set((round(b['x'], 1), round(b['y'], 1), round(b['w'], 1), round(b['l'], 1)) for b in layout)

def rotate_layout_180(layout, pallet_w, pallet_l):
    """Rotates the entire layout 180 degrees around the pallet center."""
    rotated = []
    for b in layout:
        rotated.append({
            "x": pallet_w - (b['x'] + b['w']),
            "y": pallet_l - (b['y'] + b['l']),
            "w": b['w'], "l": b['l'],
            "is_rotated": b['is_rotated']
        })
    return rotated

def flip_layout_horizontal(layout, pallet_w):
    """Flips the layout horizontally (left-to-right)."""
    flipped = []
    for b in layout:
        flipped.append({
            "x": pallet_w - (b['x'] + b['w']),
            "y": b['y'],
            "w": b['w'], "l": b['l'],
            "is_rotated": b['is_rotated']
        })
    return flipped

def center_layout(layout, pallet_w, pallet_l):
    """Calculates the bounding box of the layout and perfectly centers it on the pallet."""
    if not layout:
        return []
        
    min_x = min(b['x'] for b in layout)
    max_x = max(b['x'] + b['w'] for b in layout)
    min_y = min(b['y'] for b in layout)
    max_y = max(b['y'] + b['l'] for b in layout)
    
    layout_w = max_x - min_x
    layout_l = max_y - min_y
    
    # Calculate offsets to center the bounding box
    offset_x = (pallet_w - layout_w) / 2 - min_x
    offset_y = (pallet_l - layout_l) / 2 - min_y
    
    centered = []
    for b in layout:
        centered.append({
            "x": b['x'] + offset_x,
            "y": b['y'] + offset_y,
            "w": b['w'], "l": b['l'],
            "is_rotated": b['is_rotated']
        })
    return centered

def generate_candidate_layouts(pallet_w, pallet_l, box_w, box_l):
    """Generates uniform and mixed-orientation (Two-Block) layouts, centered on the pallet."""
    candidates = []
    
    # 1. Uniform Grids (All boxes same orientation)
    for cw, cl, is_rot in [(box_w, box_l, False), (box_l, box_w, True)]:
        cols = int(pallet_w // cw)
        rows = int(pallet_l // cl)
        if cols > 0 and rows > 0:
            layout = []
            for r in range(rows):
                for c in range(cols):
                    layout.append({"x": c * cw, "y": r * cl, "w": cw, "l": cl, "is_rotated": is_rot})
            candidates.append(center_layout(layout, pallet_w, pallet_l))
            
    # 2. Two-Block Patterns (Vertical Split - Mixed orientations)
    cols_w = int(pallet_w // box_w)
    for i in range(1, cols_w):
        w1 = i * box_w
        cols_1 = i
        rows_1 = int(pallet_l // box_l)
        
        w2 = pallet_w - w1
        cols_2 = int(w2 // box_l)
        rows_2 = int(pallet_l // box_w)
        
        if cols_1 > 0 and rows_1 > 0 and cols_2 > 0 and rows_2 > 0:
            layout = []
            for r in range(rows_1):
                for c in range(cols_1):
                    layout.append({"x": c * box_w, "y": r * box_l, "w": box_w, "l": box_l, "is_rotated": False})
            for r in range(rows_2):
                for c in range(cols_2):
                    layout.append({"x": w1 + (c * box_l), "y": r * box_w, "w": box_l, "l": box_w, "is_rotated": True})
            candidates.append(center_layout(layout, pallet_w, pallet_l))

    # 3. Two-Block Patterns (Horizontal Split - Mixed orientations)
    rows_l = int(pallet_l // box_l)
    for i in range(1, rows_l):
        l1 = i * box_l
        rows_1 = i
        cols_1 = int(pallet_w // box_w)
        
        l2 = pallet_l - l1
        rows_2 = int(l2 // box_w)
        cols_2 = int(pallet_w // box_l)
        
        if cols_1 > 0 and rows_1 > 0 and cols_2 > 0 and rows_2 > 0:
            layout = []
            for r in range(rows_1):
                for c in range(cols_1):
                    layout.append({"x": c * box_w, "y": r * box_l, "w": box_w, "l": box_l, "is_rotated": False})
            for r in range(rows_2):
                for c in range(cols_2):
                    layout.append({"x": c * box_l, "y": l1 + (r * box_w), "w": box_l, "l": box_w, "is_rotated": True})
            candidates.append(center_layout(layout, pallet_w, pallet_l))

    # Filter out any empty layouts
    valid_candidates = [c for c in candidates if len(c) > 0]
    
    if not valid_candidates:
        return []
        
    # Sort candidates by the total number of boxes they fit (Descending)
    # This ensures we don't pick a wildly inefficient layout just because it can interlock
    valid_candidates.sort(key=lambda x: len(x), reverse=True)
    max_boxes = len(valid_candidates[0])
    
    # Return only the layouts that yield the maximum possible boxes
    best_candidates = [c for c in valid_candidates if len(c) == max_boxes]
    return best_candidates

# --- Core Algorithm ---
def generate_pallet_pattern(pallet_w, pallet_l, box_w, box_l, box_h, layers, interlocking):
    if box_w > pallet_w or box_l > pallet_l:
        if box_l > pallet_w or box_w > pallet_l:
            return {"error": "Box dimensions are larger than the pallet."}

    candidates = generate_candidate_layouts(pallet_w, pallet_l, box_w, box_l)
    
    if not candidates:
        return {"error": "Boxes are too large to fit on this pallet."}

    layer_1_layout = None
    layer_2_layout = None

    if not interlocking:
        layer_1_layout = candidates[0]
        layer_2_layout = candidates[0]
    else:
        found_interlock = False
        
        for candidate in candidates:
            sig_original = get_layout_signature(candidate)
            
            rotated = rotate_layout_180(candidate, pallet_w, pallet_l)
            flipped = flip_layout_horizontal(candidate, pallet_w)
            
            sig_rotated = get_layout_signature(rotated)
            sig_flipped = get_layout_signature(flipped)
            
            if sig_original != sig_rotated:
                layer_1_layout = candidate
                layer_2_layout = rotated
                found_interlock = True
                break
            elif sig_original != sig_flipped:
                layer_1_layout = candidate
                layer_2_layout = flipped
                found_interlock = True
                break
                
        if not found_interlock:
            return {"error": "This specific box configuration perfectly divides into the pallet as a uniform block. A perfectly centered, uniform block is mathematically symmetrical and cannot generate a uniquely interlocking layer."}

    # Build final 3D JSON output
    pattern_data = []
    box_id = 1
    
    for layer in range(layers):
        z_coord = layer * box_h
        current_layout = layer_1_layout if layer % 2 == 0 else layer_2_layout
        
        for b in current_layout:
            pattern_data.append({
                "box_id": box_id,
                "layer": layer + 1,
                "x_coordinate": b['x'],
                "y_coordinate": b['y'],
                "z_coordinate": z_coord,
                "is_rotated_90_deg": b['is_rotated']
            })
            box_id += 1
            
    return pattern_data

# --- Visualization Function ---
def plot_layer(pattern_data, layer_num, pallet_w, pallet_l, box_w, box_l):
    fig, ax = plt.subplots(figsize=(6, 6 * (pallet_l / pallet_w)))
    
    pallet_rect = patches.Rectangle(
        (0, 0), pallet_w, pallet_l, 
        linewidth=2, edgecolor='black', facecolor='#8B4513', alpha=0.3
    )
    ax.add_patch(pallet_rect)
    
    layer_boxes = [box for box in pattern_data if box['layer'] == layer_num]
    
    for box in layer_boxes:
        x = box['x_coordinate']
        y = box['y_coordinate']
        rotated = box['is_rotated_90_deg']
        
        draw_w = box_l if rotated else box_w
        draw_l = box_w if rotated else box_l
        
        box_rect = patches.Rectangle(
            (x, y), draw_w, draw_l, 
            linewidth=1.5, edgecolor='black', facecolor='#4682B4', alpha=0.8
        )
        ax.add_patch(box_rect)
        
        ax.text(x + draw_w/2, y + draw_l/2, str(box['box_id']), 
                color='white', ha='center', va='center', fontweight='bold')

    ax.set_xlim(-50, pallet_w + 50)
    ax.set_ylim(-50, pallet_l + 50)
    ax.set_aspect('equal')
    ax.set_title(f"Layer {layer_num} Top-Down View")
    ax.set_xlabel("Width (mm)")
    ax.set_ylabel("Length (mm)")
    
    return fig

# --- Streamlit UI Configuration ---
st.set_page_config(page_title="Palletizing Generator", layout="wide")
st.title("📦 Python Palletizing Pattern Generator")
st.write("Generate a centered palletizing pattern with mixed-orientation interlocking checks.")

if 'pattern_data' not in st.session_state:
    st.session_state.pattern_data = None

st.sidebar.header("Pallet Dimensions")
pallet_w = st.sidebar.number_input("Pallet Width (mm)", min_value=100, value=800)
pallet_l = st.sidebar.number_input("Pallet Length (mm)", min_value=100, value=1200)

st.sidebar.header("Box Dimensions")
box_w = st.sidebar.number_input("Box Width (mm)", min_value=10, value=250) 
box_l = st.sidebar.number_input("Box Length (mm)", min_value=10, value=350)
box_h = st.sidebar.number_input("Box Height (mm)", min_value=10, value=150)

st.sidebar.header("Pattern Configuration")
layers = st.sidebar.number_input("Number of Layers", min_value=1, value=3)
interlocking = st.sidebar.checkbox("Interlocking Layers (Optimize for Stability)", value=True)

if st.sidebar.button("Generate Pattern", type="primary"):
    with st.spinner("Calculating optimal centered layouts..."):
        result = generate_pallet_pattern(
            pallet_w, pallet_l, box_w, box_l, box_h, layers, interlocking
        )
        st.session_state.pattern_data = result

if st.session_state.pattern_data:
    pattern_data = st.session_state.pattern_data
    
    if isinstance(pattern_data, dict) and "error" in pattern_data:
        st.error(pattern_data["error"])
    else:
        st.success(f"Pattern generated successfully! Total boxes: {len(pattern_data)}")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Visual Layout")
            selected_layer = st.selectbox(
                "Select Layer to View", 
                options=list(range(1, layers + 1))
            )
            
            fig = plot_layer(pattern_data, selected_layer, pallet_w, pallet_l, box_w, box_l)
            st.pyplot(fig)
            
        with col2:
            st.subheader("JSON Output")
            st.download_button(
                label="Download Pattern as JSON",
                data=json.dumps(pattern_data, indent=4),
                file_name="pallet_pattern.json",
                mime="application/json"
            )
            with st.expander("View JSON Data"):
                st.json(pattern_data)
