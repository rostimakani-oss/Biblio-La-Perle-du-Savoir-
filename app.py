
import streamlit as st
import sqlite3
import hashlib
import re
from datetime import date, datetime


# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Bibliothèque",
    page_icon="📚",
    layout="wide"
)


# =========================================================
# STYLE
# =========================================================

st.html("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
}

.stApp {
    background: #fff7fc;
}

h1, h2, h3 {
    color: #8e3a72;
    font-weight: 700;
}

[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #f5d8ea,
        #f9e8f3
    );
}

.stButton > button {
    background: #c85a9e;
    color: white;
    border: none;
    border-radius: 12px;
    font-weight: 600;
}

.stButton > button:hover {
    background: #a94482;
    color: white;
}

div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #edd3e3;
    border-radius: 16px;
    padding: 18px;
}

.card {
    background: white;
    border: 1px solid #edd3e3;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 15px;
    box-shadow: 0 3px 12px rgba(142,58,114,0.07);
}

.hero {
    background: linear-gradient(
        135deg,
        #f5d8ea,
        #fff0f8
    );
    border-radius: 20px;
    padding: 30px;
    margin-bottom: 25px;
}

</style>
""")


# =========================================================
# BASE DE DONNÉES
# =========================================================

DB = "bibliotheque.db"


def connecter():
    return sqlite3.connect(DB)


# =========================================================
# RÔLES
# =========================================================

ROLES = {

    "administrateur": [
        "accueil",
        "livres",
        "categories",
        "emprunteurs",
        "utilisateurs",
        "emprunts",
        "statistiques"
    ],

    "bibliothecaire": [
        "accueil",
        "livres",
        "categories",
        "emprunteurs",
        "emprunts",
        "statistiques"
    ],

    "emprunteur": [
        "accueil",
        "livres",
        "emprunts"
    ]
}


def a_droit(role, fonctionnalite):

    return fonctionnalite in ROLES.get(
        role,
        []
    )


# =========================================================
# VALIDATION
# =========================================================

def valider_texte(texte, champ):

    if not texte or not texte.strip():

        raise ValueError(
            f"Le champ {champ} est obligatoire."
        )


def valider_email(email):

    modele = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    if not re.match(modele, email):

        raise ValueError(
            "Adresse e-mail invalide."
        )


def valider_mot_de_passe(mot_de_passe):

    if len(mot_de_passe) < 6:

        raise ValueError(
            "Le mot de passe doit contenir "
            "au moins 6 caractères."
        )


def valider_annee(annee):

    if annee < 1000 or annee > 2100:

        raise ValueError(
            "Année invalide."
        )


# =========================================================
# MOT DE PASSE
# =========================================================

def hacher_mot_de_passe(mot_de_passe):

    return hashlib.sha256(
        mot_de_passe.encode()
    ).hexdigest()


# =========================================================
# CONNEXION
# =========================================================

def connecter_utilisateur(
    email,
    mot_de_passe
):

    connexion = connecter()
    curseur = connexion.cursor()

    mot_de_passe = hacher_mot_de_passe(
        mot_de_passe
    )

    curseur.execute("""
        SELECT
            id,
            nom,
            postnom,
            prenom,
            email,
            role
        FROM utilisateurs
        WHERE email = ?
        AND mot_de_passe = ?
    """, (
        email.strip(),
        mot_de_passe
    ))

    utilisateur = curseur.fetchone()

    connexion.close()

    return utilisateur


# =========================================================
# CATÉGORIES
# =========================================================

def obtenir_categories():

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute("""
        SELECT id, nom
        FROM categories
        ORDER BY nom
    """)

    resultats = curseur.fetchall()

    connexion.close()

    return resultats


def ajouter_categorie(nom):

    valider_texte(
        nom,
        "nom de la catégorie"
    )

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute(
        """
        INSERT INTO categories (nom)
        VALUES (?)
        """,
        (nom.strip(),)
    )

    connexion.commit()
    connexion.close()


def modifier_categorie(
    id_categorie,
    nom
):

    valider_texte(
        nom,
        "nom de la catégorie"
    )

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute("""
        UPDATE categories
        SET nom = ?
        WHERE id = ?
    """, (
        nom.strip(),
        id_categorie
    ))

    connexion.commit()
    connexion.close()


def supprimer_categorie(
    id_categorie
):

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute("""
        SELECT COUNT(*)
        FROM livres
        WHERE id_categorie = ?
    """, (id_categorie,))

    nombre = curseur.fetchone()[0]

    if nombre > 0:

        connexion.close()

        raise ValueError(
            "Impossible de supprimer une catégorie "
            "qui contient des livres."
        )

    curseur.execute("""
        DELETE FROM categories
        WHERE id = ?
    """, (id_categorie,))

    connexion.commit()
    connexion.close()


# =========================================================
# LIVRES
# =========================================================

def obtenir_livres(
    recherche=""
):

    connexion = connecter()
    curseur = connexion.cursor()

    if recherche.strip():

        recherche_sql = (
            "%" + recherche.strip() + "%"
        )

        curseur.execute("""
            SELECT
                l.id,
                l.titre,
                l.auteur,
                l.annee,
                c.nom,
                l.disponible
            FROM livres l
            LEFT JOIN categories c
            ON l.id_categorie = c.id
            WHERE l.titre LIKE ?
            OR l.auteur LIKE ?
            ORDER BY l.id DESC
        """, (
            recherche_sql,
            recherche_sql
        ))

    else:

        curseur.execute("""
            SELECT
                l.id,
                l.titre,
                l.auteur,
                l.annee,
                c.nom,
                l.disponible
            FROM livres l
            LEFT JOIN categories c
            ON l.id_categorie = c.id
            ORDER BY l.id DESC
        """)

    livres = curseur.fetchall()

    connexion.close()

    return livres


def ajouter_livre(
    titre,
    auteur,
    annee,
    id_categorie
):

    valider_texte(
        titre,
        "titre"
    )

    valider_texte(
        auteur,
        "auteur"
    )

    valider_annee(annee)

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute("""
        INSERT INTO livres
        (
            titre,
            auteur,
            annee,
            id_categorie,
            disponible
        )
        VALUES (?, ?, ?, ?, 1)
    """, (
        titre.strip(),
        auteur.strip(),
        annee,
        id_categorie
    ))

    connexion.commit()
    connexion.close()


def modifier_livre(
    id_livre,
    titre,
    auteur,
    annee,
    id_categorie
):

    valider_texte(
        titre,
        "titre"
    )

    valider_texte(
        auteur,
        "auteur"
    )

    valider_annee(annee)

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute("""
        UPDATE livres
        SET
            titre = ?,
            auteur = ?,
            annee = ?,
            id_categorie = ?
        WHERE id = ?
    """, (
        titre.strip(),
        auteur.strip(),
        annee,
        id_categorie,
        id_livre
    ))

    connexion.commit()
    connexion.close()


def supprimer_livre(id_livre):

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute("""
        SELECT disponible
        FROM livres
        WHERE id = ?
    """, (id_livre,))

    livre = curseur.fetchone()

    if livre is None:

        connexion.close()

        raise ValueError(
            "Livre introuvable."
        )

    if livre[0] == 0:

        connexion.close()

        raise ValueError(
            "Impossible de supprimer "
            "un livre actuellement emprunté."
        )

    curseur.execute("""
        DELETE FROM livres
        WHERE id = ?
    """, (id_livre,))

    connexion.commit()
    connexion.close()


# =========================================================
# EMPRUNTEURS
# =========================================================

def obtenir_emprunteurs(
    recherche=""
):

    connexion = connecter()
    curseur = connexion.cursor()

    if recherche.strip():

        q = (
            "%" +
            recherche.strip() +
            "%"
        )

        curseur.execute("""
            SELECT
                id,
                nom,
                postnom,
                prenom,
                email
            FROM utilisateurs
            WHERE role = 'emprunteur'
            AND (
                nom LIKE ?
                OR postnom LIKE ?
                OR prenom LIKE ?
                OR email LIKE ?
            )
            ORDER BY id DESC
        """, (
            q,
            q,
            q,
            q
        ))

    else:

        curseur.execute("""
            SELECT
                id,
                nom,
                postnom,
                prenom,
                email
            FROM utilisateurs
            WHERE role = 'emprunteur'
            ORDER BY id DESC
        """)

    resultats = curseur.fetchall()

    connexion.close()

    return resultats


def ajouter_emprunteur(
    nom,
    postnom,
    prenom,
    email,
    mot_de_passe
):

    valider_texte(
        nom,
        "nom"
    )

    valider_texte(
        postnom,
        "postnom"
    )

    valider_texte(
        prenom,
        "prénom"
    )

    valider_email(email)

    valider_mot_de_passe(
        mot_de_passe
    )

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute("""
        INSERT INTO utilisateurs
        (
            nom,
            postnom,
            prenom,
            email,
            mot_de_passe,
            role
        )
        VALUES (?, ?, ?, ?, ?, 'emprunteur')
    """, (
        nom.strip(),
        postnom.strip(),
        prenom.strip(),
        email.strip(),
        hacher_mot_de_passe(
            mot_de_passe
        )
    ))

    connexion.commit()
    connexion.close()


def modifier_emprunteur(
    id_utilisateur,
    nom,
    postnom,
    prenom,
    email
):

    valider_texte(
        nom,
        "nom"
    )

    valider_texte(
        postnom,
        "postnom"
    )

    valider_texte(
        prenom,
        "prénom"
    )

    valider_email(email)

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute("""
        UPDATE utilisateurs
        SET
            nom = ?,
            postnom = ?,
            prenom = ?,
            email = ?
        WHERE id = ?
        AND role = 'emprunteur'
    """, (
        nom.strip(),
        postnom.strip(),
        prenom.strip(),
        email.strip(),
        id_utilisateur
    ))

    connexion.commit()
    connexion.close()


def supprimer_emprunteur(
    id_utilisateur
):

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute("""
        SELECT COUNT(*)
        FROM emprunts
        WHERE id_utilisateur = ?
    """, (id_utilisateur,))

    nombre = curseur.fetchone()[0]

    if nombre > 0:

        connexion.close()

        raise ValueError(
            "Impossible de supprimer cet "
            "emprunteur car il possède "
            "un historique d'emprunts."
        )

    curseur.execute("""
        DELETE FROM utilisateurs
        WHERE id = ?
        AND role = 'emprunteur'
    """, (id_utilisateur,))

    connexion.commit()
    connexion.close()


# =========================================================
# UTILISATEURS
# =========================================================

def obtenir_utilisateurs():

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute("""
        SELECT
            id,
            nom,
            postnom,
            prenom,
            email,
            role
        FROM utilisateurs
        ORDER BY id DESC
    """)

    resultats = curseur.fetchall()

    connexion.close()

    return resultats


def ajouter_utilisateur(
    nom,
    postnom,
    prenom,
    email,
    mot_de_passe,
    role
):

    valider_texte(
        nom,
        "nom"
    )

    valider_texte(
        postnom,
        "postnom"
    )

    valider_texte(
        prenom,
        "prénom"
    )

    valider_email(email)

    valider_mot_de_passe(
        mot_de_passe
    )

    if role not in ROLES:

        raise ValueError(
            "Rôle invalide."
        )

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute("""
        INSERT INTO utilisateurs
        (
            nom,
            postnom,
            prenom,
            email,
            mot_de_passe,
            role
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        nom.strip(),
        postnom.strip(),
        prenom.strip(),
        email.strip(),
        hacher_mot_de_passe(
            mot_de_passe
        ),
        role
    ))

    connexion.commit()
    connexion.close()


def modifier_utilisateur(
    id_utilisateur,
    nom,
    postnom,
    prenom,
    email,
    role
):

    valider_texte(
        nom,
        "nom"
    )

    valider_texte(
        postnom,
        "postnom"
    )

    valider_texte(
        prenom,
        "prénom"
    )

    valider_email(email)

    if role not in ROLES:

        raise ValueError(
            "Rôle invalide."
        )

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute("""
        UPDATE utilisateurs
        SET
            nom = ?,
            postnom = ?,
            prenom = ?,
            email = ?,
            role = ?
        WHERE id = ?
    """, (
        nom.strip(),
        postnom.strip(),
        prenom.strip(),
        email.strip(),
        role,
        id_utilisateur
    ))

    connexion.commit()
    connexion.close()


def supprimer_utilisateur(
    id_utilisateur
):

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute("""
        SELECT COUNT(*)
        FROM emprunts
        WHERE id_utilisateur = ?
    """, (id_utilisateur,))

    nombre = curseur.fetchone()[0]

    if nombre > 0:

        connexion.close()

        raise ValueError(
            "Impossible de supprimer cet "
            "utilisateur car il possède "
            "des emprunts."
        )

    curseur.execute("""
        DELETE FROM utilisateurs
        WHERE id = ?
    """, (id_utilisateur,))

    connexion.commit()
    connexion.close()


# =========================================================
# EMPRUNTS
# =========================================================

DUREE_EMPRUNT = 14
AMENDE_PAR_JOUR = 500


def emprunter_livre(
    id_livre,
    id_utilisateur
):

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute("""
        SELECT disponible
        FROM livres
        WHERE id = ?
    """, (id_livre,))

    livre = curseur.fetchone()

    if livre is None:

        connexion.close()

        raise ValueError(
            "Livre introuvable."
        )

    if livre[0] == 0:

        connexion.close()

        raise ValueError(
            "Ce livre est déjà emprunté."
        )

    curseur.execute("""
        INSERT INTO emprunts
        (
            id_livre,
            id_utilisateur,
            date_emprunt,
            amende
        )
        VALUES (?, ?, ?, 0)
    """, (
        id_livre,
        id_utilisateur,
        date.today().isoformat()
    ))

    curseur.execute("""
        UPDATE livres
        SET disponible = 0
        WHERE id = ?
    """, (id_livre,))

    connexion.commit()
    connexion.close()


def obtenir_emprunts():

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute("""
        SELECT
            e.id,
            l.titre,
            u.nom,
            u.postnom,
            u.prenom,
            e.date_emprunt,
            e.date_retour,
            e.amende
        FROM emprunts e

        JOIN livres l
        ON e.id_livre = l.id

        JOIN utilisateurs u
        ON e.id_utilisateur = u.id

        ORDER BY e.id DESC
    """)

    resultats = curseur.fetchall()

    connexion.close()

    return resultats


def retourner_livre(
    id_emprunt
):

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute("""
        SELECT
            id_livre,
            date_emprunt
        FROM emprunts
        WHERE id = ?
        AND date_retour IS NULL
    """, (id_emprunt,))

    emprunt = curseur.fetchone()

    if emprunt is None:

        connexion.close()

        raise ValueError(
            "Emprunt introuvable ou déjà retourné."
        )

    id_livre = emprunt[0]

    date_emprunt = datetime.strptime(
        emprunt[1],
        "%Y-%m-%d"
    ).date()

    jours = (
        date.today() -
        date_emprunt
    ).days

    retard = max(
        0,
        jours - DUREE_EMPRUNT
    )

    amende = (
        retard *
        AMENDE_PAR_JOUR
    )

    curseur.execute("""
        UPDATE emprunts
        SET
            date_retour = ?,
            amende = ?
        WHERE id = ?
    """, (
        date.today().isoformat(),
        amende,
        id_emprunt
    ))

    curseur.execute("""
        UPDATE livres
        SET disponible = 1
        WHERE id = ?
    """, (id_livre,))

    connexion.commit()
    connexion.close()

    return amende


# =========================================================
# STATISTIQUES
# =========================================================

def obtenir_statistiques():

    connexion = connecter()
    curseur = connexion.cursor()

    curseur.execute(
        "SELECT COUNT(*) FROM livres"
    )
    livres = curseur.fetchone()[0]

    curseur.execute("""
        SELECT COUNT(*)
        FROM livres
        WHERE disponible = 1
    """)
    disponibles = curseur.fetchone()[0]

    curseur.execute("""
        SELECT COUNT(*)
        FROM livres
        WHERE disponible = 0
    """)
    empruntes = curseur.fetchone()[0]

    curseur.execute("""
        SELECT COUNT(*)
        FROM utilisateurs
        WHERE role = 'emprunteur'
    """)
    emprunteurs = curseur.fetchone()[0]

    curseur.execute(
        "SELECT COUNT(*) FROM categories"
    )
    categories = curseur.fetchone()[0]

    curseur.execute(
        "SELECT COUNT(*) FROM emprunts"
    )
    total_emprunts = curseur.fetchone()[0]

    curseur.execute("""
        SELECT COUNT(*)
        FROM emprunts
        WHERE date_retour IS NULL
    """)
    en_cours = curseur.fetchone()[0]

    curseur.execute("""
        SELECT COALESCE(SUM(amende), 0)
        FROM emprunts
    """)
    amendes = curseur.fetchone()[0]

    connexion.close()

    return {
        "livres": livres,
        "disponibles": disponibles,
        "empruntes": empruntes,
        "empruntes": empruntes,
        "emprunteurs": emprunteurs,
        "categories": categories,
        "emprunts": total_emprunts,
        "en_cours": en_cours,
        "amendes": amendes
    }


# =========================================================
# FONCTION ERREUR
# =========================================================

def afficher_erreur(erreur):

    st.error(
        "❌ " + str(erreur)
    )


# =========================================================
# SESSION
# =========================================================

if "utilisateur" not in st.session_state:

    st.session_state.utilisateur = None


# =========================================================
# CONNEXION
# =========================================================

if st.session_state.utilisateur is None:

    st.html("""
    <div class="hero">

        <h1><marquee behavior="scroll" direction="left" scrollamount="6">📚 Bibliothèque La Perle du Savoir</marquee></h1>

        <p style="text-align: center;">
            <b><i>Lire des livres - Lire délivre</i></b>
        </p>


    </div>
    """)

    col1, col2, col3 = st.columns(
        [1, 2, 1]
    )

    with col2:

        st.subheader(
            "🔐 Connexion"
        )

        email = st.text_input(
            "📧 Adresse e-mail",
            key="login_email"
        )

        mot_de_passe = st.text_input(
            "🔑 Mot de passe",
            type="password",
            key="login_password"
        )

        if st.button(
            "✨ Se connecter",
            use_container_width=True,
            key="login_button"
        ):

            try:

                if not email or not mot_de_passe:

                    raise ValueError(
                        "Veuillez remplir tous les champs."
                    )

                utilisateur = connecter_utilisateur(
                    email,
                    mot_de_passe
                )

                if utilisateur is None:

                    st.error(
                        "❌ E-mail ou mot de passe incorrect."
                    )

                else:

                    st.session_state.utilisateur = utilisateur

                    st.rerun()

            except Exception as erreur:

                afficher_erreur(erreur)


# =========================================================
# APPLICATION
# =========================================================

else:

    utilisateur = (
        st.session_state.utilisateur
    )

    id_utilisateur = utilisateur[0]
    nom = utilisateur[1]
    postnom = utilisateur[2]
    prenom = utilisateur[3]
    role = utilisateur[5]

    # -----------------------------------------------------
    # SIDEBAR
    # -----------------------------------------------------

    st.sidebar.markdown(
        "# 📚 Bibliothèque"
    )

    st.sidebar.markdown(
        f"### 👤 {prenom} {nom}"
    )

    st.sidebar.caption(
        f"Rôle : {role}"
    )

    st.sidebar.divider()

    menus = [

        ("🏠 Accueil", "accueil"),

        ("📚 Livres", "livres"),

        ("🏷️ Catégories", "categories"),

        ("👥 Emprunteurs", "emprunteurs"),

        ("📖 Emprunts", "emprunts"),

        ("📊 Statistiques", "statistiques"),

        ("👤 Utilisateurs", "utilisateurs")
    ]

    menus_autorises = [
        menu
        for menu, fonctionnalite in menus
        if a_droit(
            role,
            fonctionnalite
        )
    ]

    menu = st.sidebar.radio(
        "🧭 Navigation",
        menus_autorises,
        key="navigation_principale"
    )

    st.sidebar.divider()

    if st.sidebar.button(
        "🚪 Déconnexion",
        use_container_width=True,
        key="bouton_deconnexion"
    ):

        st.session_state.utilisateur = None

        st.rerun()


    # =====================================================
    # ACCUEIL
    # =====================================================

    if menu == "🏠 Accueil":

        st.title(
            "🏠 Tableau de bord"
        )

        st.html(
            f"""
            <div class="hero">
                <h2>Bienvenue, {prenom} 👋</h2>
                <p>
                    Voici le tableau de bord
                    de votre bibliothèque.
                </p>
            </div>
            """
        )

        stats = obtenir_statistiques()

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "📚 Livres",
            stats["livres"]
        )

        c2.metric(
            "🟢 Disponibles",
            stats["disponibles"]
        )

        c3.metric(
            "🔴 Empruntés",
            stats["empruntes"]
        )

        c4.metric(
            "👥 Emprunteurs",
            stats["emprunteurs"]
        )

        st.write("")

        c5, c6, c7, c8 = st.columns(4)

        c5.metric(
            "🏷️ Catégories",
            stats["categories"]
        )

        c6.metric(
            "📖 Emprunts",
            stats["emprunts"]
        )

        c7.metric(
            "⏳ En cours",
            stats["en_cours"]
        )

        c8.metric(
            "💰 Amendes",
            f'{stats["amendes"]:.0f} FC'
        )


    # =====================================================
    # LIVRES
    # =====================================================

    elif menu == "📚 Livres":

        st.title("📚 Gestion des livres")

        if role != "emprunteur":
            tab1, tab2, tab3 = st.tabs(["Catalogue", "Ajouter", "Modifier / Supprimer"])
        else:
            tab1, = st.tabs(["Catalogue"])

        # -------------------------------------------------
        # CATALOGUE
        # -------------------------------------------------
        with tab1:

            recherche = st.text_input(
                "🔎 Rechercher un titre ou un auteur",
                key="recherche_livre"
            )

            livres = obtenir_livres(recherche)

            if not livres:
                st.info("Aucun livre trouvé.")

            for livre in livres:

                categorie = livre[4] or "Non classée"
                etat = "🟢 Disponible" if livre[5] else "🔴 Emprunté"

                st.html(
                    f"""
                    <div class="card">
                        <h3>📖 {livre[1]}</h3>
                        <p><b>Auteur :</b> {livre[2]}</p>
                        <p><b>Année :</b> {livre[3]}</p>
                        <p><b>Catégorie :</b> {categorie}</p>
                        <p><b>État :</b> {etat}</p>
                    </div>
                    """
                )

        # -------------------------------------------------
        # AJOUTER & MODIFIER (Uniquement pour Admin / Biblio)
        # -------------------------------------------------
        if role != "emprunteur":

            with tab2:

                st.subheader("➕ Ajouter un livre")

                titre = st.text_input("Titre", key="ajout_livre_titre")
                auteur = st.text_input("Auteur", key="ajout_livre_auteur")
                annee = st.number_input(
                    "Année",
                    min_value=1000,
                    max_value=2100,
                    value=2026,
                    key="ajout_livre_annee"
                )

                categories = obtenir_categories()

                if not categories:
                    st.warning("Créez d'abord une catégorie.")
                else:
                    categories_dict = {c[1]: c[0] for c in categories}
                    categorie = st.selectbox(
                        "Catégorie",
                        list(categories_dict.keys()),
                        key="ajout_livre_categorie"
                    )

                    if st.button(
                        "➕ Ajouter le livre",
                        use_container_width=True,
                        key="bouton_ajout_livre"
                    ):
                        try:
                            ajouter_livre(
                                titre,
                                auteur,
                                annee,
                                categories_dict[categorie]
                            )
                            st.success("✅ Livre ajouté.")
                            st.rerun()
                        except Exception as erreur:
                            afficher_erreur(erreur)

            with tab3:

                livres = obtenir_livres()

                if livres:

                    livres_dict = {f"{l[1]} — {l[2]}": l for l in livres}

                    selection = st.selectbox(
                        "📖 Livre",
                        list(livres_dict.keys()),
                        key="selection_livre_modification"
                    )

                    livre = livres_dict[selection]

                    titre = st.text_input(
                        "Titre",
                        value=livre[1],
                        key="modification_livre_titre"
                    )

                    auteur = st.text_input(
                        "Auteur",
                        value=livre[2],
                        key="modification_livre_auteur"
                    )

                    annee = st.number_input(
                        "Année",
                        min_value=1000,
                        max_value=2100,
                        value=livre[3],
                        key="modification_livre_annee"
                    )

                    categories = obtenir_categories()

                    if categories:

                        categories_dict = {c[1]: c[0] for c in categories}
                        noms_categories = list(categories_dict.keys())
                        index = 0

                        if livre[4] in noms_categories:
                            index = noms_categories.index(livre[4])

                        categorie = st.selectbox(
                            "Catégorie",
                            noms_categories,
                            index=index,
                            key="modification_livre_categorie"
                        )

                        c1, c2 = st.columns(2)

                        with c1:
                            if st.button(
                                "💾 Modifier",
                                use_container_width=True,
                                key="bouton_modification_livre"
                            ):
                                try:
                                    modifier_livre(
                                        livre[0],
                                        titre,
                                        auteur,
                                        annee,
                                        categories_dict[categorie]
                                    )
                                    st.success("✅ Livre modifié.")
                                    st.rerun()
                                except Exception as erreur:
                                    afficher_erreur(erreur)

                        with c2:
                            if st.button(
                                "🗑️ Supprimer",
                                use_container_width=True,
                                key="bouton_suppression_livre"
                            ):
                                try:
                                    supprimer_livre(livre[0])
                                    st.success("✅ Livre supprimé.")
                                    st.rerun()
                                except Exception as erreur:
                                    afficher_erreur(erreur)
                                    
                            
                
                    

    # =====================================================
    # CATÉGORIES
    # =====================================================

    elif menu == "🏷️ Catégories":

        st.title(
            "🏷️ Gestion des catégories"
        )

        tab1, tab2, tab3 = st.tabs(
            [
                "Liste",
                "Ajouter",
                "Modifier / Supprimer"
            ]
        )

        with tab1:

            categories = obtenir_categories()

            if not categories:

                st.info(
                    "Aucune catégorie."
                )

            for categorie in categories:

                st.markdown(
                    f"""
                    <div class="card">
                        🏷️ <b>{categorie[1]}</b>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        with tab2:

            nom_categorie = st.text_input(
                "Nom de la catégorie",
                key="ajout_categorie_nom"
            )

            if st.button(
                "➕ Ajouter",
                use_container_width=True,
                key="bouton_ajout_categorie"
            ):

                try:

                    ajouter_categorie(
                        nom_categorie
                    )

                    st.success(
                        "✅ Catégorie ajoutée."
                    )

                    st.rerun()

                except Exception as erreur:

                    afficher_erreur(
                        erreur
                    )

        with tab3:

            categories = obtenir_categories()

            if categories:

                categories_dict = {
                    c[1]: c
                    for c in categories
                }

                selection = st.selectbox(
                    "Catégorie",
                    list(categories_dict.keys()),
                    key="selection_categorie_modification"
                )

                categorie = categories_dict[
                    selection
                ]

                nouveau_nom = st.text_input(
                    "Nouveau nom",
                    value=categorie[1],
                    key="modification_categorie_nom"
                )

                c1, c2 = st.columns(2)

                with c1:

                    if st.button(
                        "💾 Modifier",
                        use_container_width=True,
                        key="bouton_modification_categorie"
                    ):

                        try:

                            modifier_categorie(
                                categorie[0],
                                nouveau_nom
                            )

                            st.success(
                                "✅ Catégorie modifiée."
                            )

                            st.rerun()

                        except Exception as erreur:

                            afficher_erreur(
                                erreur
                            )

                with c2:

                    if st.button(
                        "🗑️ Supprimer",
                        use_container_width=True,
                        key="bouton_suppression_categorie"
                    ):

                        try:

                            supprimer_categorie(
                                categorie[0]
                            )

                            st.success(
                                "✅ Catégorie supprimée."
                            )

                            st.rerun()

                        except Exception as erreur:

                            afficher_erreur(
                                erreur
                            )


    # =====================================================
    # EMPRUNTEURS
    # =====================================================

    elif menu == "👥 Emprunteurs":

        st.title(
            "👥 Gestion des emprunteurs"
        )

        tab1, tab2, tab3 = st.tabs(
            [
                "Liste",
                "Ajouter",
                "Modifier / Supprimer"
            ]
        )

        with tab1:

            recherche = st.text_input(
                "🔎 Rechercher",
                key="recherche_emprunteur"
            )

            emprunteurs = obtenir_emprunteurs(
                recherche
            )

            if not emprunteurs:

                st.info(
                    "Aucun emprunteur."
                )

            for emprunteur in emprunteurs:

                st.html(
                    f"""
                    <div class="card">

                        <h3>
                            👤 {emprunteur[1]}
                            {emprunteur[2]}
                            {emprunteur[3]}
                        </h3>

                        <p>
                            📧 {emprunteur[4]}
                        </p>

                    </div>
                    """
                )

        with tab2:

            nom_emp = st.text_input(
                "Nom",
                key="ajout_emprunteur_nom"
            )

            postnom_emp = st.text_input(
                "Postnom",
                key="ajout_emprunteur_postnom"
            )

            prenom_emp = st.text_input(
                "Prénom",
                key="ajout_emprunteur_prenom"
            )

            email_emp = st.text_input(
                "E-mail",
                key="ajout_emprunteur_email"
            )

            password_emp = st.text_input(
                "Mot de passe",
                type="password",
                key="ajout_emprunteur_password"
            )

            if st.button(
                "➕ Ajouter l'emprunteur",
                use_container_width=True,
                key="bouton_ajout_emprunteur"
            ):

                try:

                    ajouter_emprunteur(
                        nom_emp,
                        postnom_emp,
                        prenom_emp,
                        email_emp,
                        password_emp
                    )

                    st.success(
                        "✅ Emprunteur ajouté."
                    )

                    st.rerun()

                except Exception as erreur:

                    afficher_erreur(
                        erreur
                    )

        with tab3:

            emprunteurs = obtenir_emprunteurs()

            if emprunteurs:

                emprunteurs_dict = {
                    f"{e[1]} {e[2]} {e[3]}": e
                    for e in emprunteurs
                }

                selection = st.selectbox(
                    "Emprunteur",
                    list(emprunteurs_dict.keys()),
                    key="selection_emprunteur_modification"
                )

                emprunteur = emprunteurs_dict[
                    selection
                ]

                nom_emp = st.text_input(
                    "Nom",
                    value=emprunteur[1],
                    key="modification_emprunteur_nom"
                )

                postnom_emp = st.text_input(
                    "Postnom",
                    value=emprunteur[2],
                    key="modification_emprunteur_postnom"
                )

                prenom_emp = st.text_input(
                    "Prénom",
                    value=emprunteur[3],
                    key="modification_emprunteur_prenom"
                )

                email_emp = st.text_input(
                    "E-mail",
                    value=emprunteur[4],
                    key="modification_emprunteur_email"
                )

                c1, c2 = st.columns(2)

                with c1:

                    if st.button(
                        "💾 Modifier",
                        use_container_width=True,
                        key="bouton_modification_emprunteur"
                    ):

                        try:

                            modifier_emprunteur(
                                emprunteur[0],
                                nom_emp,
                                postnom_emp,
                                prenom_emp,
                                email_emp
                            )

                            st.success(
                                "✅ Emprunteur modifié."
                            )

                            st.rerun()

                        except Exception as erreur:

                            afficher_erreur(
                                erreur
                            )

                with c2:

                    if st.button(
                        "🗑️ Supprimer",
                        use_container_width=True,
                        key="bouton_suppression_emprunteur"
                    ):

                        try:

                            supprimer_emprunteur(
                                emprunteur[0]
                            )

                            st.success(
                                "✅ Emprunteur supprimé."
                            )

                            st.rerun()

                        except Exception as erreur:

                            afficher_erreur(
                                erreur
                            )


    # =====================================================
    # EMPRUNTS
    # =====================================================

    elif menu == "📖 Emprunts":

        st.title(
            "📖 Gestion des emprunts"
        )

        tab1, tab2, tab3 = st.tabs(
            [
                "Historique",
                "Nouvel emprunt",
                "Retour"
            ]
        )

        with tab1:

            emprunts = obtenir_emprunts()

            if not emprunts:

                st.info(
                    "Aucun emprunt."
                )

            for emprunt in emprunts:

                statut = (
                    "🟢 Retourné"
                    if emprunt[6]
                    else "🔴 En cours"
                )

                st.html(
                    f"""
                    <div class="card">

                        <h3>
                            📖 {emprunt[1]}
                        </h3>

                        <p>
                            👤 {emprunt[2]}
                            {emprunt[3]}
                            {emprunt[4]}
                        </p>

                        <p>
                            📅 Emprunt :
                            {emprunt[5]}
                        </p>

                        <p>
                            🔄 Retour :
                            {emprunt[6] or "En cours"}
                        </p>

                        <p>
                            {statut}
                        </p>

                        <p>
                            💰 Amende :
                            {emprunt[7]:.0f} FC
                        </p>

                    </div>
                    """
                )

        with tab2:

            livres_disponibles = [
                livre
                for livre in obtenir_livres()
                if livre[5] == 1
            ]

            if not livres_disponibles:

                st.warning(
                    "Aucun livre disponible."
                )

            else:

                livres_dict = {
                    f"{l[1]} — {l[2]}": l[0]
                    for l in livres_disponibles
                }

                livre_selection = st.selectbox(
                    "📚 Livre",
                    list(livres_dict.keys()),
                    key="emprunt_livre_selection"
                )

                if role == "emprunteur":

                    id_emprunteur = id_utilisateur

                    st.info(
                        "L'emprunt sera enregistré "
                        "à votre nom."
                    )

                else:

                    emprunteurs = obtenir_emprunteurs()

                    if emprunteurs:

                        emprunteurs_dict = {
                            f"{e[1]} {e[2]} {e[3]}": e[0]
                            for e in emprunteurs
                        }

                        emprunteur_selection = st.selectbox(
                            "👤 Emprunteur",
                            list(emprunteurs_dict.keys()),
                            key="emprunt_emprunteur_selection"
                        )

                        id_emprunteur = emprunteurs_dict[
                            emprunteur_selection
                        ]

                    else:

                        id_emprunteur = None

                        st.warning(
                            "Aucun emprunteur enregistré."
                        )

                if st.button(
                    "📖 Enregistrer l'emprunt",
                    use_container_width=True,
                    key="bouton_ajout_emprunt"
                ):

                    try:

                        if id_emprunteur is None:

                            raise ValueError(
                                "Aucun emprunteur sélectionné."
                            )

                        emprunter_livre(
                            livres_dict[
                                livre_selection
                            ],
                            id_emprunteur
                        )

                        st.success(
                            "✅ Emprunt enregistré."
                        )

                        st.rerun()

                    except Exception as erreur:

                        afficher_erreur(
                            erreur
                        )

        with tab3:

            emprunts_actifs = [
                e
                for e in obtenir_emprunts()
                if e[6] is None
            ]

            if not emprunts_actifs:

                st.info(
                    "Aucun emprunt en cours."
                )

            else:

                emprunts_dict = {
                    f"{e[1]} — {e[2]} {e[3]}": e[0]
                    for e in emprunts_actifs
                }

                selection = st.selectbox(
                    "📖 Emprunt à retourner",
                    list(emprunts_dict.keys()),
                    key="retour_emprunt_selection"
                )

                if st.button(
                    "🔄 Enregistrer le retour",
                    use_container_width=True,
                    key="bouton_retour_emprunt"
                ):

                    try:

                        amende = retourner_livre(
                            emprunts_dict[
                                selection
                            ]
                        )

                        if amende > 0:

                            st.warning(
                                f"⚠️ Retour enregistré. "
                                f"Amende : {amende:.0f} FC"
                            )

                        else:

                            st.success(
                                "✅ Retour enregistré "
                                "sans amende."
                            )

                        st.rerun()

                    except Exception as erreur:

                        afficher_erreur(
                            erreur
                        )


    # =====================================================
    # STATISTIQUES
    # =====================================================

    elif menu == "📊 Statistiques":

        st.title(
            "📊 Statistiques"
        )

        stats = obtenir_statistiques()

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "📚 Livres",
            stats["livres"]
        )

        c2.metric(
            "🟢 Disponibles",
            stats["disponibles"]
        )

        c3.metric(
            "🔴 Empruntés",
            stats["empruntes"]
        )

        c4.metric(
            "👥 Emprunteurs",
            stats["emprunteurs"]
        )

        st.write("")

        c5, c6, c7, c8 = st.columns(4)

        c5.metric(
            "🏷️ Catégories",
            stats["categories"]
        )

        c6.metric(
            "📖 Emprunts",
            stats["emprunts"]
        )

        c7.metric(
            "⏳ En cours",
            stats["en_cours"]
        )

        c8.metric(
            "💰 Amendes",
            f'{stats["amendes"]:.0f} FC'
        )


    # =====================================================
    # UTILISATEURS
    # =====================================================

    elif menu == "👤 Utilisateurs":

        st.title(
            "👤 Gestion des utilisateurs"
        )

        tab1, tab2, tab3 = st.tabs(
            [
                "Liste",
                "Ajouter",
                "Modifier / Supprimer"
            ]
        )

        with tab1:

            utilisateurs = obtenir_utilisateurs()

            if not utilisateurs:

                st.info(
                    "Aucun utilisateur."
                )

            for utilisateur_item in utilisateurs:

                icone = {
                    "administrateur": "👑",
                    "bibliothecaire": "📚",
                    "emprunteur": "👤"
                }.get(
                    utilisateur_item[5],
                    "👤"
                )

                st.html(
                    f"""
                    <div class="card">

                        <h3>
                            {icone}
                            {utilisateur_item[1]}
                            {utilisateur_item[2]}
                            {utilisateur_item[3]}
                        </h3>

                        <p>
                            📧 {utilisateur_item[4]}
                        </p>

                        <p>
                            🔐 Rôle :
                            {utilisateur_item[5]}
                        </p>

                    </div>
                    """
                )

        with tab2:

            nom_user = st.text_input(
                "Nom",
                key="ajout_utilisateur_nom"
            )

            postnom_user = st.text_input(
                "Postnom",
                key="ajout_utilisateur_postnom"
            )

            prenom_user = st.text_input(
                "Prénom",
                key="ajout_utilisateur_prenom"
            )

            email_user = st.text_input(
                "E-mail",
                key="ajout_utilisateur_email"
            )

            password_user = st.text_input(
                "Mot de passe",
                type="password",
                key="ajout_utilisateur_password"
            )

            role_user = st.selectbox(
                "Rôle",
                list(ROLES.keys()),
                key="ajout_utilisateur_role"
            )

            if st.button(
                "➕ Créer l'utilisateur",
                use_container_width=True,
                key="bouton_ajout_utilisateur"
            ):

                try:

                    ajouter_utilisateur(
                        nom_user,
                        postnom_user,
                        prenom_user,
                        email_user,
                        password_user,
                        role_user
                    )

                    st.success(
                        "✅ Utilisateur créé."
                    )

                    st.rerun()

                except Exception as erreur:

                    afficher_erreur(
                        erreur
                    )

        with tab3:

            utilisateurs = obtenir_utilisateurs()

            if utilisateurs:

                utilisateurs_dict = {
                    f"{u[1]} {u[2]} {u[3]} — {u[5]}": u
                    for u in utilisateurs
                }

                selection = st.selectbox(
                    "Utilisateur",
                    list(utilisateurs_dict.keys()),
                    key="selection_utilisateur_modification"
                )

                utilisateur_modifie = utilisateurs_dict[
                    selection
                ]

                nom_user = st.text_input(
                    "Nom",
                    value=utilisateur_modifie[1],
                    key="modification_utilisateur_nom"
                )

                postnom_user = st.text_input(
                    "Postnom",
                    value=utilisateur_modifie[2],
                    key="modification_utilisateur_postnom"
                )

                prenom_user = st.text_input(
                    "Prénom",
                    value=utilisateur_modifie[3],
                    key="modification_utilisateur_prenom"
                )

                email_user = st.text_input(
                    "E-mail",
                    value=utilisateur_modifie[4],
                    key="modification_utilisateur_email"
                )

                roles = list(
                    ROLES.keys()
                )

                index_role = 0

                if utilisateur_modifie[5] in roles:

                    index_role = roles.index(
                        utilisateur_modifie[5]
                    )

                role_user = st.selectbox(
                    "Rôle",
                    roles,
                    index=index_role,
                    key="modification_utilisateur_role"
                )

                c1, c2 = st.columns(2)

                with c1:

                    if st.button(
                        "💾 Modifier",
                        use_container_width=True,
                        key="bouton_modification_utilisateur"
                    ):

                        try:

                            modifier_utilisateur(
                                utilisateur_modifie[0],
                                nom_user,
                                postnom_user,
                                prenom_user,
                                email_user,
                                role_user
                            )

                            st.success(
                                "✅ Utilisateur modifié."
                            )

                            st.rerun()

                        except Exception as erreur:

                            afficher_erreur(
                                erreur
                            )

                with c2:

                    if st.button(
                        "🗑️ Supprimer",
                        use_container_width=True,
                        key="bouton_suppression_utilisateur"
                    ):

                        try:

                            if utilisateur_modifie[0] == id_utilisateur:

                                raise ValueError(
                                    "Vous ne pouvez pas "
                                    "supprimer votre propre compte."
                                )

                            supprimer_utilisateur(
                                utilisateur_modifie[0]
                            )

                            st.success(
                                "✅ Utilisateur supprimé."
                            )

                            st.rerun()

                        except Exception as erreur:

                            afficher_erreur(
                                erreur
                            )
