import streamlit as st

from src.utils.public_labels import (
    LABEL_MODE_SESSION_KEY,
    NEIGHBORHOOD_LABEL_MODE,
    PUBLIC_LABEL_MODE,
    get_label_mode,
)


def render_label_mode_control() -> str:
    current_mode = get_label_mode(st.secrets, st.session_state)

    if LABEL_MODE_SESSION_KEY not in st.session_state:
        st.session_state[LABEL_MODE_SESSION_KEY] = current_mode

    options = {
        "Neighborhood labels": NEIGHBORHOOD_LABEL_MODE,
        "Public tract keys": PUBLIC_LABEL_MODE,
    }

    current_label = next(
        label for label, value in options.items()
        if value == st.session_state[LABEL_MODE_SESSION_KEY]
    )

    selection = st.sidebar.radio(
        "Display labels",
        options=list(options.keys()),
        index=list(options.keys()).index(current_label),
        help="Switch between real neighborhood/tract display names and the public tract key labels.",
    )

    st.session_state[LABEL_MODE_SESSION_KEY] = options[selection]

    if st.session_state[LABEL_MODE_SESSION_KEY] == PUBLIC_LABEL_MODE:
        st.sidebar.caption("Public mode uses masked tract identifiers such as `TRACT-053`.")
    else:
        st.sidebar.caption("Neighborhood mode shows the original tract display labels from the data.")

    return st.session_state[LABEL_MODE_SESSION_KEY]
