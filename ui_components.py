import streamlit as st

def render_sidebar_header(card_border, accent, secondary):
    st.markdown(f"""
    <div style="
        padding: 20px 0 16px 0;
        border-bottom: 2px solid {card_border};
        margin-bottom: 20px;
    ">
        <div style="
            font-size: 1.1rem;
            font-weight: 700;
            color: {accent};
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 6px;
        ">
            <span style="font-size: 1.3rem;">🔌</span>
            <span>Connection Manager</span>
        </div>
        <div style="
            font-size: 0.85rem;
            color: {secondary};
            font-weight: 400;
        ">
            Configure your database connection
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_connection_status(cfg, card_border, secondary, connected=True):
    st.markdown(f"""
    <div style="
        margin-top: 32px;
        padding-top: 20px;
        border-top: 2px solid {card_border};
    ">
        <div style="
            font-size: 0.85rem;
            font-weight: 600;
            color: {secondary};
            margin-bottom: 12px;
        ">
            CONNECTION STATUS
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Status indicator
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(72, 187, 120, 0.3);
    ">
        <div style="
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        ">
            <span style="
                font-size: 1.2rem;
            ">✅</span>
            <span style="
                color: white;
                font-weight: 700;
                font-size: 0.95rem;
            ">Connected</span>
        </div>
        <div style="
            color: rgba(255, 255, 255, 0.95);
            font-size: 0.85rem;
            line-height: 1.6;
        ">
            <div style="margin-bottom: 4px;">
                <strong>Type:</strong> {cfg['type']}
            </div>
            <div style="margin-bottom: 4px;">
                <strong>Server:</strong> {cfg['host']}:{cfg['port']}
            </div>
            <div>
                <strong>Database:</strong> {cfg.get('database', 'N/A')}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_main_header(gradient_primary, accent, secondary):
    st.markdown(f"""
    <div style="
        text-align: center; 
        margin-bottom: 20px;
        padding: 8px 24px;
        animation: fadeInUp 0.8s ease-out;
    ">
        <h1 style="
            font-size: 3.5rem;
            font-weight: 900;
            margin-bottom: 15px;
            display: inline-block;
            letter-spacing: -0.04em;
            line-height: 1;
        ">
            <span style="
                background: {gradient_primary};
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-shadow: 0 4px 30px {accent}40;
                filter: drop-shadow(0 0 20px {accent}30);
            ">✨ Ask Questions. Get Answers  </span>
            <span style="
                color: #1a202c;
                text-shadow: none;
                filter: none;
                font-style: italic;
            ">from your database.</span>
            <span style="
                background: {gradient_primary};
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-shadow: 0 4px 30px {accent}40;
                filter: drop-shadow(0 0 20px {accent}30);
            "> ✨</span>
        </h1>
        <div style="
            font-size: 1.25rem;
            font-weight: 500;
            color: {secondary};
            max-width: 650px;
            margin: 0 auto;
            line-height: 1.7;
            letter-spacing: 0.02em;
        ">
            Transform natural language into powerful SQL queries instantly with our AI Agent
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_schema_browser(accent, secondary, root_text, tables, schema_objects):
    st.markdown(f"""
    <div style="margin-bottom: 20px;">
        <div style="
            font-size: 1.15rem; 
            font-weight: 700; 
            color: {accent}; 
            display: flex; 
            align-items: center; 
            gap: 10px;
            margin-bottom: 8px;
        ">
            🗄️ Database Schema
        </div>
        <div style="
            font-size: 0.9rem; 
            color: {secondary}; 
            line-height: 1.5;
            font-weight: 400;
        ">
            Browse tables and columns
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if not tables:
        st.warning("⚠ No tables found in database.")
        return None
    
    selected_table = st.selectbox("Select Table", tables, label_visibility="collapsed")
    
    if selected_table:
        st.markdown(f"""
        <div style="
            font-size: 0.95rem;
            font-weight: 600;
            color: {root_text};
            margin: 20px 0 12px 0;
        ">
            Columns in <code style="
                background: {accent}15;
                color: {accent};
                padding: 3px 8px;
                border-radius: 6px;
                font-size: 0.9em;
            ">{selected_table}</code>
        </div>
        """, unsafe_allow_html=True)
        cols = schema_objects.get(selected_table, [])
        
        # Render columns as chips
        chip_html = ""
        for c in cols:
            chip_html += f'<span class="col-chip">{c}</span>'
        st.markdown(chip_html, unsafe_allow_html=True)
        st.markdown("---")
    return selected_table
