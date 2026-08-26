import streamlit as st
import sqlite3
import hashlib
import re
from datetime import date, datetime

# =========================================================
# CONFIGURATION ET STYLE
# =========================================================

st.set_page_config(
    page_title="Bibliothèque",
    page_icon="📚",
    layout="wide"
)

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
    background: linear-gradient(180deg, #f5d8ea, #f9e8f3);
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
    background: linear-gradient(135deg, #f5d8ea, #fff0f8);
    border-radius: 20px;
    padding: 30px;
    margin-bottom: 25px;
}
</style>
""")


# =========================================================
# EXCEPTIONS PERSONNALISÉES
# =========================================================

class BibliothequeException(Exception):
    """Exception de base de l'application"""
    pass

class ValidationException(BibliothequeException):
    """Exception levée en cas d'erreur de saisie ou de formatage"""
    pass

class MetierException(BibliothequeException):
    """Exception levée en cas de violation d'une règle de gestion"""
    pass


# =========================================================
# POO : MODÈLES DE DONNÉES & ENCAPSULATION
# =========================================================

class Utilisateur:
    """Classe représentant un utilisateur du système (Admin, Bibliothécaire, Emprunteur)"""
    def __init__(self, id_user, nom, postnom, prenom, email, role):
        self._id = id_user
        self._nom = self._valider_texte(nom, "nom")
        self._postnom = self._valider_texte(postnom, "postnom")
        self._prenom = self._valider_texte(prenom, "prénom")
        self._email = None
        self.email = email
        self._role = role

    @property
    def id(self): return self._id
    @property
    def nom(self): return self._nom
    @property
    def postnom(self): return self._postnom
    @property
    def prenom(self): return self._prenom
    @property
    def role(self): return self._role

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, valeur):
        modele = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not valeur or not re.match(modele, valeur.strip()):
            raise ValidationException("Adresse e-mail invalide.")
        self._email = valeur.strip()

    @staticmethod
    def _valider_texte(texte, champ):
        if not texte or not texte.strip():
            raise ValidationException(f"Le champ {champ} est obligatoire.")
        return texte.strip()

    @staticmethod
    def hacher_mot_de_passe(mot_de_passe):
        if len(mot_de_passe) < 6:
            raise ValidationException("Le mot de passe doit contenir au moins 6 caractères.")
        return hashlib.sha256(mot_de_passe.encode()).hexdigest()


class Categorie:
    """Classe représentant une catégorie de livres"""
    def __init__(self, id_cat, nom):
        self._id = id_cat
        self._nom = None
        self.nom = nom

    @property
    def id(self): return self._id
    @property
    def nom(self): return self._nom

    @nom.setter
    def nom(self, valeur):
        if not valeur or not valeur.strip():
            raise ValidationException("Le nom de la catégorie est obligatoire.")
        self._nom = valeur.strip()


class Livre:
    """Classe représentant un livre"""
    def __init__(self, id_livre, titre, auteur, annee, id_categorie, disponible=True, nom_categorie=None):
        self._id = id_livre
        self._titre = None
        self._auteur = None
        self._annee = None
        self.titre = titre
        self.auteur = auteur
        self.annee = annee
        self.id_categorie = id_categorie
        self.disponible = disponible
        self.nom_categorie = nom_categorie

    @property
    def id(self): return self._id
    @property
    def titre(self): return self._titre
    @property
    def auteur(self): return self._auteur
    @property
    def annee(self): return self._annee

    @titre.setter
    def titre(self, val):
        if not val or not val.strip(): raise ValidationException("Le titre est obligatoire.")
        self._titre = val.strip()

    @auteur.setter
    def auteur(self, val):
        if not val or not val.strip(): raise ValidationException("L'auteur est obligatoire.")
        self._auteur = val.strip()

    @annee.setter
    def annee(self, val):
        if val is not None and (val < 1000 or val > 2100):
            raise ValidationException("Année invalide.")
        self._annee = val


# =========================================================
# GESTIONNAIRE DE BASE DE DONNÉES ET SERVICES
# =========================================================

class DatabaseManager:
    DB_NAME = "bibliotheque.db"

    @classmethod
    def connecter(cls):
        return sqlite3.connect(cls.DB_NAME)

    @classmethod
    def init_db(cls):
        conn = cls.connecter()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL UNIQUE
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS utilisateurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                postnom TEXT NOT NULL,
                prenom TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                mot_de_passe TEXT NOT NULL,
                role TEXT NOT NULL
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS livres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titre TEXT NOT NULL,
                auteur TEXT NOT NULL,
                annee INTEGER,
                id_categorie INTEGER,
                disponible INTEGER DEFAULT 1,
                FOREIGN KEY(id_categorie) REFERENCES categories(id)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS emprunts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_livre INTEGER NOT NULL,
                id_utilisateur INTEGER NOT NULL,
                date_emprunt TEXT NOT NULL,
                date_retour TEXT,
                amende REAL DEFAULT 0,
                FOREIGN KEY(id_livre) REFERENCES livres(id),
                FOREIGN KEY(id_utilisateur) REFERENCES utilisateurs(id)
            );
        """)
        conn.commit()
        conn.close()

DatabaseManager.init_db()


class BibliothequeService:
    DUREE_EMPRUNT = 14
    AMENDE_PAR_JOUR = 500

    ROLES = {
        "administrateur": ["accueil", "livres", "categories", "emprunteurs", "utilisateurs", "emprunts", "statistiques"],
        "bibliothecaire": ["accueil", "livres", "categories", "emprunteurs", "emprunts", "statistiques"],
        "emprunteur": ["accueil", "livres", "emprunts"]
    }

    @classmethod
    def a_droit(cls, role, fonctionnalite):
        return fonctionnalite in cls.ROLES.get(role, [])

    # --- Authentification ---
    @staticmethod
    def connecter_utilisateur(email, mot_de_passe):
        if not email or not mot_de_passe:
            raise ValidationException("Veuillez remplir tous les champs.")
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        hash_pass = Utilisateur.hacher_mot_de_passe(mot_de_passe)
        cur.execute("""
            SELECT id, nom, postnom, prenom, email, role
            FROM utilisateurs WHERE email = ? AND mot_de_passe = ?
        """, (email.strip(), hash_pass))
        res = cur.fetchone()
        conn.close()
        if res:
            return Utilisateur(*res)
        return None

    # --- Catégories ---
    @staticmethod
    def obtenir_categories():
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        cur.execute("SELECT id, nom FROM categories ORDER BY nom")
        rows = cur.fetchall()
        conn.close()
        return [Categorie(r[0], r[1]) for r in rows]

    @staticmethod
    def ajouter_categorie(nom):
        cat = Categorie(None, nom)
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO categories (nom) VALUES (?)", (cat.nom,))
            conn.commit()
        except sqlite3.IntegrityError:
            raise MetierException("Cette catégorie existe déjà.")
        finally:
            conn.close()

    @staticmethod
    def modifier_categorie(id_cat, nom):
        cat = Categorie(id_cat, nom)
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        cur.execute("UPDATE categories SET nom = ? WHERE id = ?", (cat.nom, cat.id))
        conn.commit()
        conn.close()

    @staticmethod
    def supprimer_categorie(id_cat):
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM livres WHERE id_categorie = ?", (id_cat,))
        if cur.fetchone()[0] > 0:
            conn.close()
            raise MetierException("Impossible de supprimer une catégorie qui contient des livres.")
        cur.execute("DELETE FROM categories WHERE id = ?", (id_cat,))
        conn.commit()
        conn.close()

    # --- Livres ---
    @staticmethod
    def obtenir_livres(recherche=""):
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        if recherche.strip():
            q = f"%{recherche.strip()}%"
            cur.execute("""
                SELECT l.id, l.titre, l.auteur, l.annee, l.id_categorie, l.disponible, c.nom
                FROM livres l LEFT JOIN categories c ON l.id_categorie = c.id
                WHERE l.titre LIKE ? OR l.auteur LIKE ? ORDER BY l.id DESC
            """, (q, q))
        else:
            cur.execute("""
                SELECT l.id, l.titre, l.auteur, l.annee, l.id_categorie, l.disponible, c.nom
                FROM livres l LEFT JOIN categories c ON l.id_categorie = c.id ORDER BY l.id DESC
            """)
        rows = cur.fetchall()
        conn.close()
        return [Livre(r[0], r[1], r[2], r[3], r[4], bool(r[5]), r[6]) for r in rows]

    @staticmethod
    def ajouter_livre(titre, auteur, annee, id_categorie):
        livre = Livre(None, titre, auteur, annee, id_categorie)
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO livres (titre, auteur, annee, id_categorie, disponible)
            VALUES (?, ?, ?, ?, 1)
        """, (livre.titre, livre.auteur, livre.annee, livre.id_categorie))
        conn.commit()
        conn.close()

    @staticmethod
    def modifier_livre(id_livre, titre, auteur, annee, id_categorie):
        livre = Livre(id_livre, titre, auteur, annee, id_categorie)
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        cur.execute("""
            UPDATE livres SET titre = ?, auteur = ?, annee = ?, id_categorie = ?
            WHERE id = ?
        """, (livre.titre, livre.auteur, livre.annee, livre.id_categorie, livre.id))
        conn.commit()
        conn.close()

    @staticmethod
    def supprimer_livre(id_livre):
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        cur.execute("SELECT disponible FROM livres WHERE id = ?", (id_livre,))
        row = cur.fetchone()
        if not row:
            conn.close()
            raise MetierException("Livre introuvable.")
        if row[0] == 0:
            conn.close()
            raise MetierException("Impossible de supprimer un livre actuellement emprunté.")
        cur.execute("DELETE FROM livres WHERE id = ?", (id_livre,))
        conn.commit()
        conn.close()

    # --- Utilisateurs & Emprunteurs ---
    @staticmethod
    def obtenir_utilisateurs():
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        cur.execute("SELECT id, nom, postnom, prenom, email, role FROM utilisateurs ORDER BY id DESC")
        rows = cur.fetchall()
        conn.close()
        return [Utilisateur(*r) for r in rows]

    @staticmethod
    def obtenir_emprunteurs(recherche=""):
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        if recherche.strip():
            q = f"%{recherche.strip()}%"
            cur.execute("""
                SELECT id, nom, postnom, prenom, email, role
                FROM utilisateurs WHERE role = 'emprunteur'
                AND (nom LIKE ? OR postnom LIKE ? OR prenom LIKE ? OR email LIKE ?)
                ORDER BY id DESC
            """, (q, q, q, q))
        else:
            cur.execute("""
                SELECT id, nom, postnom, prenom, email, role
                FROM utilisateurs WHERE role = 'emprunteur' ORDER BY id DESC
            """)
        rows = cur.fetchall()
        conn.close()
        return [Utilisateur(*r) for r in rows]

    @staticmethod
    def ajouter_utilisateur(nom, postnom, prenom, email, mot_de_passe, role):
        user = Utilisateur(None, nom, postnom, prenom, email, role)
        hash_pass = Utilisateur.hacher_mot_de_passe(mot_de_passe)
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO utilisateurs (nom, postnom, prenom, email, mot_de_passe, role)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user.nom, user.postnom, user.prenom, user.email, hash_pass, user.role))
            conn.commit()
        except sqlite3.IntegrityError:
            raise MetierException("Cet email est déjà utilisé.")
        finally:
            conn.close()

    @staticmethod
    def modifier_utilisateur(id_user, nom, postnom, prenom, email, role):
        user = Utilisateur(id_user, nom, postnom, prenom, email, role)
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        cur.execute("""
            UPDATE utilisateurs SET nom = ?, postnom = ?, prenom = ?, email = ?, role = ?
            WHERE id = ?
        """, (user.nom, user.postnom, user.prenom, user.email, user.role, user.id))
        conn.commit()
        conn.close()

    @staticmethod
    def supprimer_utilisateur(id_user):
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM emprunts WHERE id_utilisateur = ?", (id_user,))
        if cur.fetchone()[0] > 0:
            conn.close()
            raise MetierException("Impossible de supprimer cet utilisateur car il possède un historique d'emprunts.")
        cur.execute("DELETE FROM utilisateurs WHERE id = ?", (id_user,))
        conn.commit()
        conn.close()

    # --- Emprunts ---
    @staticmethod
    def emprunter_livre(id_livre, id_utilisateur):
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        cur.execute("SELECT disponible FROM livres WHERE id = ?", (id_livre,))
        row = cur.fetchone()
        if not row:
            conn.close()
            raise MetierException("Livre introuvable.")
        if row[0] == 0:
            conn.close()
            raise MetierException("Ce livre est déjà emprunté.")
        cur.execute("""
            INSERT INTO emprunts (id_livre, id_utilisateur, date_emprunt, amende)
            VALUES (?, ?, ?, 0)
        """, (id_livre, id_utilisateur, date.today().isoformat()))
        cur.execute("UPDATE livres SET disponible = 0 WHERE id = ?", (id_livre,))
        conn.commit()
        conn.close()

    @staticmethod
    def obtenir_emprunts():
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        cur.execute("""
            SELECT e.id, l.titre, u.nom, u.postnom, u.prenom, e.date_emprunt, e.date_retour, e.amende
            FROM emprunts e
            JOIN livres l ON e.id_livre = l.id
            JOIN utilisateurs u ON e.id_utilisateur = u.id
            ORDER BY e.id DESC
        """)
        rows = cur.fetchall()
        conn.close()
        return rows

    @classmethod
    def retourner_livre(cls, id_emprunt):
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        cur.execute("""
            SELECT id_livre, date_emprunt FROM emprunts
            WHERE id = ? AND date_retour IS NULL
        """, (id_emprunt,))
        emprunt = cur.fetchone()
        if not emprunt:
            conn.close()
            raise MetierException("Emprunt introuvable ou déjà retourné.")

        id_livre, date_emprunt_str = emprunt[0], emprunt[1]
        date_emp = datetime.strptime(date_emprunt_str, "%Y-%m-%d").date()
        jours = (date.today() - date_emp).days
        retard = max(0, jours - cls.DUREE_EMPRUNT)
        amende = retard * cls.AMENDE_PAR_JOUR

        cur.execute("""
            UPDATE emprunts SET date_retour = ?, amende = ? WHERE id = ?
        """, (date.today().isoformat(), amende, id_emprunt))
        cur.execute("UPDATE livres SET disponible = 1 WHERE id = ?", (id_livre,))
        conn.commit()
        conn.close()
        return amende

    @staticmethod
    def obtenir_statistiques():
        conn = DatabaseManager.connecter()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM livres"); livres = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM livres WHERE disponible = 1"); disponibles = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM utilisateurs WHERE role = 'emprunteur'"); emprunteurs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM categories"); categories = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM emprunts"); total_emprunts = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM emprunts WHERE date_retour IS NULL"); en_cours = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(amende), 0) FROM emprunts"); amendes = cur.fetchone()[0]
        conn.close()

        return {
            "livres": livres,
            "disponibles": disponibles,
            "empruntes": livres - disponibles,
            "emprunteurs": emprunteurs,
            "categories": categories,
            "emprunts": total_emprunts,
            "en_cours": en_cours,
            "amendes": amendes
        }


# =========================================================
# APPLICATION STREAMLIT (INTERFACE UTILISATEUR)
# =========================================================

def afficher_erreur(erreur):
    st.error(f"❌ {erreur}")

if "utilisateur" not in st.session_state:
    st.session_state.utilisateur = None


# --- ACCÈS SANS SESSION (CONNEXION) ---
if st.session_state.utilisateur is None:
    st.html("""
    <div class="hero">
        <h1><marquee behavior="scroll" direction="left" scrollamount="6">📚 Bibliothèque La Perle du Savoir</marquee></h1>
        <p style="text-align: center;"><b><i>Lire des livres - Lire délivre</i></b></p>
    </div>
    """)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("🔐 Connexion")
        email = st.text_input("📧 Adresse e-mail", key="login_email")
        mot_de_passe = st.text_input("🔑 Mot de passe", type="password", key="login_password")

        if st.button("✨ Se connecter", use_container_width=True, key="login_button"):
            try:
                user = BibliothequeService.connecter_utilisateur(email, mot_de_passe)
                if user is None:
                    st.error("❌ E-mail ou mot de passe incorrect.")
                else:
                    st.session_state.utilisateur = user
                    st.rerun()
            except BibliothequeException as e:
                afficher_erreur(e)


# --- ACCÈS AVEC SESSION (APPLICATION COMPLÈTE) ---
else:
    user = st.session_state.utilisateur

    # -----------------------------------------------------
    # SIDEBAR
    # -----------------------------------------------------
    st.sidebar.markdown("# 📚 Bibliothèque")
    st.sidebar.markdown(f"### 👤 {user.prenom} {user.nom}")
    st.sidebar.caption(f"Rôle : {user.role}")
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

    menus_autorises = [m[0] for m in menus if BibliothequeService.a_droit(user.role, m[1])]
    menu = st.sidebar.radio("🧭 Navigation", menus_autorises, key="navigation_principale")

    st.sidebar.divider()
    if st.sidebar.button("🚪 Déconnexion", use_container_width=True, key="bouton_deconnexion"):
        st.session_state.utilisateur = None
        st.rerun()

    # -----------------------------------------------------
    # MENU : ACCUEIL
    # -----------------------------------------------------
    if menu == "🏠 Accueil":
        st.title("🏠 Tableau de bord")
        st.html(f"""
        <div class="hero">
            <h2>Bienvenue, {user.prenom} 👋</h2>
            <p>Voici le tableau de bord de votre bibliothèque.</p>
        </div>
        """)

        stats = BibliothequeService.obtenir_statistiques()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📚 Livres", stats["livres"])
        c2.metric("🟢 Disponibles", stats["disponibles"])
        c3.metric("🔴 Empruntés", stats["empruntes"])
        c4.metric("👥 Emprunteurs", stats["emprunteurs"])

        st.write("")
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("🏷️ Catégories", stats["categories"])
        c6.metric("📖 Emprunts", stats["emprunts"])
        c7.metric("⏳ En cours", stats["en_cours"])
        c8.metric("💰 Amendes", f"{stats['amendes']:.0f} FC")

    # -----------------------------------------------------
    # MENU : LIVRES
    # -----------------------------------------------------
    elif menu == "📚 Livres":
        st.title("📚 Gestion des livres")

        if user.role == "emprunteur":
            tab1, = st.tabs(["Catalogue"])
        else:
            tab1, tab2, tab3 = st.tabs(["Catalogue", "Ajouter", "Modifier / Supprimer"])

        with tab1:
            recherche = st.text_input("🔎 Rechercher un titre ou un auteur", key="recherche_livre")
            livres = BibliothequeService.obtenir_livres(recherche)

            if not livres:
                st.info("Aucun livre trouvé.")
            for livre in livres:
                etat = "🟢 Disponible" if livre.disponible else "🔴 Emprunté"
                annee_str = str(livre.annee) if livre.annee is not None else "Non renseignée"
                st.html(f"""
                <div class="card">
                    <h3>📖 {livre.titre}</h3>
                    <p><b>Auteur :</b> {livre.auteur}</p>
                    <p><b>Année :</b> {annee_str}</p>
                    <p><b>Catégorie :</b> {livre.nom_categorie or 'Non classée'}</p>
                    <p><b>État :</b> {etat}</p>
                </div>
                """)

        if user.role != "emprunteur":
            with tab2:
                st.subheader("➕ Ajouter un livre")
                titre = st.text_input("Titre", key="ajout_livre_titre")
                auteur = st.text_input("Auteur", key="ajout_livre_auteur")
                annee = st.number_input("Année", min_value=1000, max_value=2100, value=2026, key="ajout_livre_annee")
                categories = BibliothequeService.obtenir_categories()

                if not categories:
                    st.warning("Créez d'abord une catégorie.")
                else:
                    cats_dict = {c.nom: c.id for c in categories}
                    categorie_sel = st.selectbox("Catégorie", list(cats_dict.keys()), key="ajout_livre_categorie")

                    if st.button("➕ Ajouter le livre", use_container_width=True, key="bouton_ajout_livre"):
                        try:
                            BibliothequeService.ajouter_livre(titre, auteur, annee, cats_dict[categorie_sel])
                            st.success("✅ Livre ajouté.")
                            st.rerun()
                        except BibliothequeException as e:
                            afficher_erreur(e)

            with tab3:
                livres = BibliothequeService.obtenir_livres()
                if livres:
                    livres_dict = {f"{l.titre} — {l.auteur}": l for l in livres}
                    selection = st.selectbox("📖 Livre", list(livres_dict.keys()), key="selection_livre_mod")
                    livre_sel = livres_dict[selection]

                    titre = st.text_input("Titre", value=livre_sel.titre, key="mod_livre_titre")
                    auteur = st.text_input("Auteur", value=livre_sel.auteur, key="mod_livre_auteur")
                    annee_valeur = livre_sel.annee if livre_sel.annee is not None else 2026
                    annee = st.number_input("Année", min_value=1000, max_value=2100, value=annee_valeur, key="mod_livre_annee")
                    categories = BibliothequeService.obtenir_categories()

                    if categories:
                        cats_dict = {c.nom: c.id for c in categories}
                        noms_cats = list(cats_dict.keys())
                        index = noms_cats.index(livre_sel.nom_categorie) if livre_sel.nom_categorie in noms_cats else 0
                        cat_sel = st.selectbox("Catégorie", noms_cats, index=index, key="mod_livre_cat")

                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("💾 Modifier", use_container_width=True, key="bouton_mod_livre"):
                                try:
                                    BibliothequeService.modifier_livre(livre_sel.id, titre, auteur, annee, cats_dict[cat_sel])
                                    st.success("✅ Livre modifié.")
                                    st.rerun()
                                except BibliothequeException as e:
                                    afficher_erreur(e)
                        with c2:
                            if st.button("🗑️ Supprimer", use_container_width=True, key="bouton_sup_livre"):
                                try:
                                    BibliothequeService.supprimer_livre(livre_sel.id)
                                    st.success("✅ Livre supprimé.")
                                    st.rerun()
                                except BibliothequeException as e:
                                    afficher_erreur(e)

    # -----------------------------------------------------
    # MENU : CATÉGORIES
    # -----------------------------------------------------
    elif menu == "🏷️ Catégories":
        st.title("🏷️ Gestion des catégories")
        tab1, tab2, tab3 = st.tabs(["Liste", "Ajouter", "Modifier / Supprimer"])

        with tab1:
            categories = BibliothequeService.obtenir_categories()
            if not categories:
                st.info("Aucune catégorie.")
            for cat in categories:
                st.markdown(f'<div class="card">🏷️ <b>{cat.nom}</b></div>', unsafe_allow_html=True)

        with tab2:
            nom_cat = st.text_input("Nom de la catégorie", key="ajout_cat_nom")
            if st.button("➕ Ajouter", use_container_width=True, key="bouton_ajout_cat"):
                try:
                    BibliothequeService.ajouter_categorie(nom_cat)
                    st.success("✅ Catégorie ajoutée.")
                    st.rerun()
                except BibliothequeException as e:
                    afficher_erreur(e)

        with tab3:
            categories = BibliothequeService.obtenir_categories()
            if categories:
                cats_dict = {c.nom: c for c in categories}
                selection = st.selectbox("Catégorie", list(cats_dict.keys()), key="selection_cat_mod")
                cat_sel = cats_dict[selection]

                nouveau_nom = st.text_input("Nouveau nom", value=cat_sel.nom, key="mod_cat_nom")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("💾 Modifier", use_container_width=True, key="bouton_mod_cat"):
                        try:
                            BibliothequeService.modifier_categorie(cat_sel.id, nouveau_nom)
                            st.success("✅ Catégorie modifiée.")
                            st.rerun()
                        except BibliothequeException as e:
                            afficher_erreur(e)
                with c2:
                    if st.button("🗑️ Supprimer", use_container_width=True, key="bouton_sup_cat"):
                        try:
                            BibliothequeService.supprimer_categorie(cat_sel.id)
                            st.success("✅ Catégorie supprimée.")
                            st.rerun()
                        except BibliothequeException as e:
                            afficher_erreur(e)

    # -----------------------------------------------------
    # MENU : EMPRUNTEURS
    # -----------------------------------------------------
    elif menu == "👥 Emprunteurs":
        st.title("👥 Gestion des emprunteurs")
        tab1, tab2, tab3 = st.tabs(["Liste", "Ajouter", "Modifier / Supprimer"])

        with tab1:
            recherche = st.text_input("🔎 Rechercher", key="recherche_emp")
            emprunteurs = BibliothequeService.obtenir_emprunteurs(recherche)
            if not emprunteurs:
                st.info("Aucun emprunteur.")
            for emp in emprunteurs:
                st.html(f"""
                <div class="card">
                    <h3>👤 {emp.nom} {emp.postnom} {emp.prenom}</h3>
                    <p>📧 {emp.email}</p>
                </div>
                """)

        with tab2:
            nom = st.text_input("Nom", key="ajout_emp_nom")
            postnom = st.text_input("Postnom", key="ajout_emp_postnom")
            prenom = st.text_input("Prénom", key="ajout_emp_prenom")
            email = st.text_input("E-mail", key="ajout_emp_email")
            pwd = st.text_input("Mot de passe", type="password", key="ajout_emp_pwd")

            if st.button("➕ Ajouter l'emprunteur", use_container_width=True, key="bouton_ajout_emp"):
                try:
                    BibliothequeService.ajouter_utilisateur(nom, postnom, prenom, email, pwd, "emprunteur")
                    st.success("✅ Emprunteur ajouté.")
                    st.rerun()
                except BibliothequeException as e:
                    afficher_erreur(e)

        with tab3:
            emprunteurs = BibliothequeService.obtenir_emprunteurs()
            if emprunteurs:
                emp_dict = {f"{e.nom} {e.postnom} {e.prenom}": e for e in emprunteurs}
                selection = st.selectbox("Emprunteur", list(emp_dict.keys()), key="selection_emp_mod")
                emp_sel = emp_dict[selection]

                nom = st.text_input("Nom", value=emp_sel.nom, key="mod_emp_nom")
                postnom = st.text_input("Postnom", value=emp_sel.postnom, key="mod_emp_postnom")
                prenom = st.text_input("Prénom", value=emp_sel.prenom, key="mod_emp_prenom")
                email = st.text_input("E-mail", value=emp_sel.email, key="mod_emp_email")

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("💾 Modifier", use_container_width=True, key="bouton_mod_emp"):
                        try:
                            BibliothequeService.modifier_utilisateur(emp_sel.id, nom, postnom, prenom, email, "emprunteur")
                            st.success("✅ Emprunteur modifié.")
                            st.rerun()
                        except BibliothequeException as e:
                            afficher_erreur(e)
                with c2:
                    if st.button("🗑️ Supprimer", use_container_width=True, key="bouton_sup_emp"):
                        try:
                            BibliothequeService.supprimer_utilisateur(emp_sel.id)
                            st.success("✅ Emprunteur supprimé.")
                            st.rerun()
                        except BibliothequeException as e:
                            afficher_erreur(e)

    # -----------------------------------------------------
    # MENU : EMPRUNTS
    # -----------------------------------------------------
    elif menu == "📖 Emprunts":
        st.title("📖 Gestion des emprunts")
        tab1, tab2, tab3 = st.tabs(["Historique", "Nouvel emprunt", "Retour"])

        with tab1:
            emprunts = BibliothequeService.obtenir_emprunts()
            if not emprunts:
                st.info("Aucun emprunt.")
            for emp in emprunts:
                statut = "🟢 Retourné" if emp[6] else "🔴 En cours"
                st.html(f"""
                <div class="card">
                    <h3>📖 {emp[1]}</h3>
                    <p>👤 {emp[2]} {emp[3]} {emp[4]}</p>
                    <p>📅 Emprunt : {emp[5]}</p>
                    <p>🔄 Retour : {emp[6] or 'En cours'}</p>
                    <p>{statut}</p>
                    <p>💰 Amende : {emp[7]:.0f} FC</p>
                </div>
                """)

        with tab2:
            livres_dispo = [l for l in BibliothequeService.obtenir_livres() if l.disponible]
            if not livres_dispo:
                st.warning("Aucun livre disponible.")
            else:
                livres_dict = {f"{l.titre} — {l.auteur}": l.id for l in livres_dispo}
                livre_sel = st.selectbox("📚 Livre", list(livres_dict.keys()), key="emprunt_livre_sel")

                if user.role == "emprunteur":
                    id_emp = user.id
                    st.info("L'emprunt sera enregistré à votre nom.")
                else:
                    emprunteurs = BibliothequeService.obtenir_emprunteurs()
                    if emprunteurs:
                        emp_dict = {f"{e.nom} {e.postnom} {e.prenom}": e.id for e in emprunteurs}
                        emp_sel = st.selectbox("👤 Emprunteur", list(emp_dict.keys()), key="emprunt_emp_sel")
                        id_emp = emp_dict[emp_sel]
                    else:
                        id_emp = None
                        st.warning("Aucun emprunteur enregistré.")

                if st.button("📖 Enregistrer l'emprunt", use_container_width=True, key="bouton_ajout_emprunt"):
                    try:
                        if id_emp is None: raise ValidationException("Aucun emprunteur sélectionné.")
                        BibliothequeService.emprunter_livre(livres_dict[livre_sel], id_emp)
                        st.success("✅ Emprunt enregistré.")
                        st.rerun()
                    except BibliothequeException as e:
                        afficher_erreur(e)

        with tab3:
            emprunts_actifs = [e for e in BibliothequeService.obtenir_emprunts() if e[6] is None]
            if not emprunts_actifs:
                st.info("Aucun emprunt en cours.")
            else:
                emp_actifs_dict = {f"{e[1]} — {e[2]} {e[3]}": e[0] for e in emprunts_actifs}
                selection = st.selectbox("📖 Emprunt à retourner", list(emp_actifs_dict.keys()), key="retour_emp_sel")

                if st.button("🔄 Enregistrer le retour", use_container_width=True, key="bouton_retour_emp"):
                    try:
                        amende = BibliothequeService.retourner_livre(emp_actifs_dict[selection])
                        if amende > 0:
                            st.warning(f"⚠️ Retour enregistré. Amende : {amende:.0f} FC")
                        else:
                            st.success("✅ Retour enregistré sans amende.")
                        st.rerun()
                    except BibliothequeException as e:
                        afficher_erreur(e)

    # -----------------------------------------------------
    # MENU : STATISTIQUES
    # -----------------------------------------------------
    elif menu == "📊 Statistiques":
        st.title("📊 Statistiques")
        stats = BibliothequeService.obtenir_statistiques()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📚 Livres", stats["livres"])
        c2.metric("🟢 Disponibles", stats["disponibles"])
        c3.metric("🔴 Empruntés", stats["empruntes"])
        c4.metric("👥 Emprunteurs", stats["emprunteurs"])

        st.write("")
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("🏷️ Catégories", stats["categories"])
        c6.metric("📖 Emprunts", stats["emprunts"])
        c7.metric("⏳ En cours", stats["en_cours"])
        c8.metric("💰 Amendes", f"{stats['amendes']:.0f} FC")

    # -----------------------------------------------------
    # MENU : UTILISATEURS
    # -----------------------------------------------------
    elif menu == "👤 Utilisateurs":
        st.title("👤 Gestion des utilisateurs")
        tab1, tab2, tab3 = st.tabs(["Liste", "Ajouter", "Modifier / Supprimer"])

        with tab1:
            utilisateurs = BibliothequeService.obtenir_utilisateurs()
            if not utilisateurs:
                st.info("Aucun utilisateur.")
            for u in utilisateurs:
                icone = {"administrateur": "👑", "bibliothecaire": "📚", "emprunteur": "👤"}.get(u.role, "👤")
                st.html(f"""
                <div class="card">
                    <h3>{icone} {u.nom} {u.postnom} {u.prenom}</h3>
                    <p>📧 {u.email}</p>
                    <p>🔐 Rôle : {u.role}</p>
                </div>
                """)

        with tab2:
            nom = st.text_input("Nom", key="ajout_user_nom")
            postnom = st.text_input("Postnom", key="ajout_user_postnom")
            prenom = st.text_input("Prénom", key="ajout_user_prenom")
            email = st.text_input("E-mail", key="ajout_user_email")
            pwd = st.text_input("Mot de passe", type="password", key="ajout_user_pwd")
            role_sel = st.selectbox("Rôle", list(BibliothequeService.ROLES.keys()), key="ajout_user_role")

            if st.button("➕ Créer l'utilisateur", use_container_width=True, key="bouton_ajout_user"):
                try:
                    BibliothequeService.ajouter_utilisateur(nom, postnom, prenom, email, pwd, role_sel)
                    st.success("✅ Utilisateur créé.")
                    st.rerun()
                except BibliothequeException as e:
                    afficher_erreur(e)

        with tab3:
            utilisateurs = BibliothequeService.obtenir_utilisateurs()
            if utilisateurs:
                users_dict = {f"{u.nom} {u.postnom} {u.prenom} — {u.role}": u for u in utilisateurs}
                selection = st.selectbox("Utilisateur", list(users_dict.keys()), key="selection_user_mod")
                user_sel = users_dict[selection]

                nom = st.text_input("Nom", value=user_sel.nom, key="mod_user_nom")
                postnom = st.text_input("Postnom", value=user_sel.postnom, key="mod_user_postnom")
                prenom = st.text_input("Prénom", value=user_sel.prenom, key="mod_user_prenom")
                email = st.text_input("E-mail", value=user_sel.email, key="mod_user_email")
                roles_list = list(BibliothequeService.ROLES.keys())
                idx_role = roles_list.index(user_sel.role) if user_sel.role in roles_list else 0
                role_sel = st.selectbox("Rôle", roles_list, index=idx_role, key="mod_user_role")

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("💾 Modifier", use_container_width=True, key="bouton_mod_user"):
                        try:
                            BibliothequeService.modifier_utilisateur(user_sel.id, nom, postnom, prenom, email, role_sel)
                            st.success("✅ Utilisateur modifié.")
                            st.rerun()
                        except BibliothequeException as e:
                            afficher_erreur(e)
                with c2:
                    if st.button("🗑️ Supprimer", use_container_width=True, key="bouton_sup_user"):
                        try:
                            if user_sel.id == user.id:
                                raise MetierException("Vous ne pouvez pas supprimer votre propre compte.")
                            BibliothequeService.supprimer_utilisateur(user_sel.id)
                            st.success("✅ Utilisateur supprimé.")
                            st.rerun()
                        except BibliothequeException as e:
                            afficher_erreur(e)