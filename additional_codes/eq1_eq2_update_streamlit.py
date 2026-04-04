import numpy as np
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Eq1 Eq2 Visualizer", layout="wide")

st.title("Eq. (1) and Eq. (2) Visualization")

st.markdown(r"""
### Eq. (1)
\[
f_{bulk}=Ac^2(1-c)^2+B_\eta\eta^2(1-\eta)^2+B_\phi\phi^2(1-\phi)^2+B_{\eta\phi}\eta^2\phi^2
\]

### Eq. (2)
\[
f =
h(\eta)A_\alpha(c-0.99)^2
+
h(\phi)A_\beta(c-0.01)^2
+
W\eta^2\phi^2
+
B_\eta\eta^2(1-\eta)^2
+
B_\phi\phi^2(1-\phi)^2
\]

\[
h(\xi)=\xi^3(6\xi^2-15\xi+10)
\]
""")

with st.sidebar:
    st.header("Parameters")

    # Eq1
    A = st.slider("A", 0.1, 20.0, 5.0)
    B_eta = st.slider("B_eta", 0.0, 20.0, 2.0)
    B_phi = st.slider("B_phi", 0.0, 20.0, 2.0)
    B_etaphi = st.slider("B_eta_phi", 0.0, 20.0, 2.0)

    # Eq2
    A_alpha = st.slider("A_alpha", 0.1, 20.0, 5.0)
    A_beta = st.slider("A_beta", 0.1, 20.0, 5.0)
    W = st.slider("W", 0.0, 20.0, 2.0)

    # fixed
    fixed_c = st.slider("Fixed c", 0.0, 1.0, 0.5)
    fixed_eta = st.slider("Fixed eta", 0.0, 1.0, 0.5)
    fixed_phi = st.slider("Fixed phi", 0.0, 1.0, 0.5)

n = 100

c = np.linspace(0,1,n)
eta = np.linspace(0,1,n)
phi = np.linspace(0,1,n)

def h(x):
    return x**3*(6*x**2 - 15*x + 10)

def f_bulk(c,eta,phi):
    return (
        A*c**2*(1-c)**2 +
        B_eta*eta**2*(1-eta)**2 +
        B_phi*phi**2*(1-phi)**2 +
        B_etaphi*eta**2*phi**2
    )

def f_eq2(c,eta,phi):
    return (
        h(eta)*A_alpha*(c-0.99)**2 +
        h(phi)*A_beta*(c-0.01)**2 +
        W*eta**2*phi**2 +
        B_eta*eta**2*(1-eta)**2 +
        B_phi*phi**2*(1-phi)**2
    )

def plot_surface(X,Y,Z,title,xlabel,ylabel):
    fig = go.Figure(data=[go.Surface(x=X,y=Y,z=Z)])
    fig.update_layout(
        title=title,
        scene=dict(xaxis_title=xlabel,yaxis_title=ylabel,zaxis_title="f"),
        margin=dict(l=0,r=0,b=0,t=40)
    )
    return fig

st.header("Eq (1)")

C,ETA = np.meshgrid(c,eta)
Z1 = f_bulk(C,ETA,fixed_phi)
st.plotly_chart(plot_surface(C,ETA,Z1,"f_bulk(c,eta)","c","eta"),width="stretch")

st.header("Eq (2)")

C,ETA = np.meshgrid(c,eta)
Z2 = f_eq2(C,ETA,fixed_phi)
st.plotly_chart(plot_surface(C,ETA,Z2,"f(c,eta) Eq2","c","eta"),width="stretch")
