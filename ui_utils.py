"""
UI Styling utilities for AskSQL application
"""
from pathlib import Path


def load_css_with_theme(theme_vars: dict) -> str:
    """
    Load CSS file and inject theme variables
    
    Args:
        theme_vars: Dictionary of theme variables (ROOT_BG, ACCENT, etc.)
    
    Returns:
        CSS string with theme variables injected
    """
    css_file = Path(__file__).parent / "assets" / "styles.css"
    
    with open(css_file, 'r') as f:
        css = f.read()
    
    # Build dynamic CSS with theme variables
    dynamic_css = f"""
    <style>
    /* Theme-specific variables */
    .stApp {{
        background: {theme_vars['ROOT_BG']};
        color: {theme_vars['ROOT_TEXT']};
    }}
    
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
        color: {theme_vars['ROOT_TEXT']};
        text-shadow: 0 2px 20px {theme_vars['ACCENT']}30;
    }}
    
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {{
        background: {theme_vars['CARD_BG']};
        border: 2px solid {theme_vars['CARD_BORDER']};
        box-shadow: {theme_vars['SHADOW']}, inset 0 1px 0 rgba(255, 255, 255, 0.1);
    }}
    
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"]::before {{
        background: linear-gradient(90deg, transparent, {theme_vars['ACCENT']}60, transparent);
    }}
    
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"]:hover {{
        box-shadow: {theme_vars['GLOW']}, {theme_vars['SHADOW']};
        border-color: {theme_vars['ACCENT']}60;
    }}
    
    .col-chip {{
        background: {theme_vars['GRADIENT_ACCENT']};
        box-shadow: 0 4px 15px {theme_vars['ACCENT']}40;
    }}
    
    .col-chip:hover {{
        box-shadow: 0 8px 25px {theme_vars['ACCENT']}60;
    }}
    
    .stButton button {{
        background: {theme_vars['GRADIENT_PRIMARY']};
        box-shadow: 0 8px 30px {theme_vars['ACCENT']}50, inset 0 1px 0 rgba(255, 255, 255, 0.2);
    }}
    
    .stButton button:hover {{
        box-shadow: {theme_vars['GLOW']}, 0 12px 40px {theme_vars['ACCENT']}60;
    }}
    
    .stTextInput label, .stSelectbox label, .stNumberInput label, .stCheckbox label {{
        color: {theme_vars['ROOT_TEXT']} !important;
    }}
    
    .stTextInput input, .stTextArea textarea, .stSelectbox select {{
        background: {theme_vars['INPUT_BG']};
        border: 2px solid {theme_vars['CARD_BORDER']};
        color: {theme_vars['ROOT_TEXT']};
    }}
    
    .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus {{
        border-color: {theme_vars['ACCENT']};
        box-shadow: 0 0 0 4px {theme_vars['ACCENT']}20, {theme_vars['GLOW']};
    }}
    
    [data-testid="stSidebar"] {{
        background: {theme_vars['CARD_BG']};
        border-right: 2px solid {theme_vars['CARD_BORDER']};
    }}
    
    [data-testid="stSidebar"] .stRadio label p,
    [data-testid="stSidebar"] .stCheckbox label p,
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .streamlit-expanderHeader p,
    [data-testid="stSidebar"] .streamlit-expanderHeader,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary span,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary p {{
        color: {theme_vars['ROOT_TEXT']} !important;
    }}
    
    /* Force Expander Arrow Color for both themes - High Specificity */
    [data-testid="stExpander"] summary svg {{
        fill: {theme_vars['EXPANDER_ARROW']} !important;
        color: {theme_vars['EXPANDER_ARROW']} !important;
        stroke: {theme_vars['EXPANDER_ARROW']} !important;
    }}
    
    [data-testid="stExpander"] summary svg path {{
        fill: {theme_vars['EXPANDER_ARROW']} !important;
        stroke: {theme_vars['EXPANDER_ARROW']} !important;
    }}
    
    [data-testid="stExpander"] details summary svg {{
        fill: {theme_vars['EXPANDER_ARROW']} !important;
        color: {theme_vars['EXPANDER_ARROW']} !important;
        stroke: {theme_vars['EXPANDER_ARROW']} !important;
    }}
    
    [data-testid="stSidebar"] .stRadio label {{
        background: {theme_vars['INPUT_BG']};
        border: 2px solid {theme_vars['CARD_BORDER']};
    }}
    
    [data-testid="stSidebar"] .stRadio label:hover {{
        border-color: {theme_vars['ACCENT']};
        background: {theme_vars['ACCENT']}15;
        box-shadow: 0 4px 15px {theme_vars['ACCENT']}30;
    }}
    
    .stCodeBlock {{
        background: {theme_vars['CARD_BG']};
        border: 2px solid {theme_vars['CARD_BORDER']};
        box-shadow: {theme_vars['SHADOW']};
    }}
    
    code {{
        background: {theme_vars['GRADIENT_ACCENT']};
        box-shadow: 0 2px 8px {theme_vars['ACCENT']}40;
    }}
    
    .stDataFrame {{
        box-shadow: {theme_vars['SHADOW']};
        border: 2px solid {theme_vars['CARD_BORDER']};
    }}
    
    .stSuccess, .stInfo, .stWarning {{
        border-left: 5px solid {theme_vars['SUCCESS']};
        background: {theme_vars['CARD_BG']};
    }}
    
    .streamlit-expanderHeader {{
        background: {theme_vars['CARD_BG']};
        border: 2px solid {theme_vars['CARD_BORDER']};
    }}
    
    .streamlit-expanderHeader:hover {{
        border-color: {theme_vars['ACCENT']};
        background: {theme_vars['ACCENT']}15;
        box-shadow: 0 4px 20px {theme_vars['ACCENT']}30;
    }}
    
    hr {{
        background: {theme_vars['GRADIENT_ACCENT']};
        box-shadow: 0 2px 15px {theme_vars['ACCENT']}40;
    }}
    
    ::-webkit-scrollbar-track {{
        background: {theme_vars['ROOT_BG_SOLID']};
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: {theme_vars['GRADIENT_ACCENT']};
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: {theme_vars['ACCENT']};
    }}
    
    .stDownloadButton button {{
        background: {theme_vars['GRADIENT_ACCENT']};
        box-shadow: 0 6px 20px {theme_vars['ACCENT']}40;
    }}
    
    .stDownloadButton button:hover {{
        box-shadow: 0 8px 30px {theme_vars['ACCENT']}60;
        transform: translateY(-3px);
    }}
    
    {css}
    </style>
    
    <script>
    // Enable browser password manager
    document.addEventListener('DOMContentLoaded', function() {{
        const inputs = document.querySelectorAll('input[type="password"]');
        inputs.forEach(input => {{
            input.setAttribute('autocomplete', 'current-password');
        }});
        
        const userInputs = document.querySelectorAll('input[aria-label*="User"]');
        userInputs.forEach(input => {{
            input.setAttribute('autocomplete', 'username');
        }});
    }});
    </script>
    """
    
    return dynamic_css
