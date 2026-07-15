# C'est Quoi Ça ? — MVP

App Streamlit qui identifie un objet à partir d'une photo (quoi / pourquoi / comment l'utiliser) via l'IA vision Gemini (gratuite).

## 1. Tester en local (optionnel mais recommandé avant de déployer)

```bash
# 1. Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate      # sur Windows : venv\Scripts\activate

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Copier le fichier secrets et y coller ta clé
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# puis ouvrir .streamlit/secrets.toml et remplacer par ta vraie clé Gemini

# 4. Lancer l'app
streamlit run app.py
```

L'app s'ouvre sur http://localhost:8501

## 2. Obtenir une clé Gemini gratuite (2 min, sans carte bancaire)

1. Aller sur https://aistudio.google.com
2. Se connecter avec un compte Google
3. Cliquer sur "Get API key" → "Create API key"
4. Copier la clé

## 3. Déployer sur Streamlit Cloud (gratuit)

### Étape A — Mettre le code sur GitHub

```bash
git init
git add .
git commit -m "MVP C'est Quoi Ça"
```

Puis créer un nouveau repo sur https://github.com/new (peut être privé ou public), et pousser :

```bash
git remote add origin https://github.com/TON-USERNAME/NOM-DU-REPO.git
git branch -M main
git push -u origin main
```

⚠️ Le fichier `.gitignore` empêche déjà d'envoyer ta clé secrète et la base `scans.db` sur GitHub — ne les ajoute jamais manuellement.

### Étape B — Déployer

1. Aller sur https://share.streamlit.io
2. Se connecter avec GitHub
3. Cliquer sur "New app"
4. Choisir ton repo, la branche `main`, et le fichier `app.py`
5. Cliquer sur "Advanced settings" → **Secrets** → coller :

```toml
GEMINI_API_KEY = "ta-vraie-cle-ici"
```

6. Cliquer sur "Deploy"

L'app sera en ligne en 1 à 2 minutes, avec une URL du type :
`https://ton-app.streamlit.app`

## 4. Après le déploiement

- Chaque push sur `main` redéploie automatiquement l'app.
- La base SQLite (`scans.db`) est recréée à chaque redéploiement sur Streamlit Cloud (stockage non permanent) — normal pour un MVP, à changer plus tard (ex: Supabase/Postgres) si tu veux un historique qui survit aux redéploiements.
- Limite gratuite Gemini : environ 1500 requêtes/jour, largement suffisant pour valider le MVP.
