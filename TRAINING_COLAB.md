# Training Model di Google Colab (GRATIS)

Karena disk lokal penuh, gunakan Google Colab yang menyediakan GPU gratis.

## Langkah-langkah:

### 1. Buka Google Colab

https://colab.research.google.com/

### 2. Buat Notebook Baru dan Copy Code Ini:

```python
# ============================================================
# CELL 1: Setup
# ============================================================
!pip install scikit-learn pandas numpy tensorflow

# Upload dataset_gabungan.csv ke Colab (klik ikon folder -> upload)
# Atau mount Google Drive jika file ada di Drive

# ============================================================
# CELL 2: Preprocessing Functions
# ============================================================
import re, pickle, numpy as np, pandas as pd, tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from tensorflow.keras.layers import (
    Input, Embedding, Conv1D, GlobalMaxPooling1D,
    Concatenate, Dense, Dropout
)
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Model

LABEL_CUES = r"""
    hoax|hoaks|penipuan|tipuan|disinformasi|misinformasi|
    palsu|fitnah|provokasi|bohong|tidak\s+benar|
    klarifikasi|cek\s+fakta|factcheck
"""

DOMAIN_TOKENS = r"""
    turnbackhoax|turnbackhoaxid|
    kompas|kompascom|kompas\.com|
    detik|detikcom|liputan6|tribunnews|
    cnnindonesia|tempo|tempo\.co|merdeka|antaranews|komdigi
"""

URL_TOKENS = r"http|https|www|com|id|html|htm|php|bitly|bit\.ly|archive"

def clean_text(s: str) -> str:
    """Preprocessing PERSIS seperti di preprocess.py"""
    s = str(s)
    s = re.sub(r"\[[^]]*\]", " ", s)
    s = s.lower()
    s = re.sub(r"http\S+|www\.\S+", " ", s)
    s = re.sub(rf"\b({DOMAIN_TOKENS})\b", " ", s, flags=re.IGNORECASE | re.VERBOSE)
    s = re.sub(rf"\b({URL_TOKENS})\b", " ", s, flags=re.IGNORECASE | re.VERBOSE)
    s = re.sub(rf"\b({LABEL_CUES})\b", " ", s, flags=re.IGNORECASE | re.VERBOSE)
    s = re.sub(r"[^a-z\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def build_mkcnn(vocab_size, embed_dim=100, max_len=150,
                filters=128, kernels=(2,3,4,5), dropout=0.3):
    inp = Input(shape=(max_len,), name="inp")
    x = Embedding(vocab_size, embed_dim, name="emb")(inp)

    branches = []
    for k in kernels:
        c = Conv1D(filters, k, activation="relu", padding="valid", name=f"conv_k{k}")(x)
        p = GlobalMaxPooling1D(name=f"gap_k{k}")(c)
        branches.append(p)

    h = Concatenate(name="concat")(branches)
    h = Dropout(dropout, name="drop")(h)
    h = Dense(128, activation="relu", name="dense")(h)
    out = Dense(1, activation="sigmoid", name="cls")(h)

    model = Model(inp, out, name="MultiKernel1DCNN")
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model

# ============================================================
# CELL 3: Load & Preprocess Data
# ============================================================
# UPLOAD FILE dataset_gabungan.csv terlebih dahulu!
# Jika di Drive:
# from google.colab import drive
# drive.mount('/content/drive')
# df = pd.read_csv('/content/drive/MyDrive/dataset_gabungan.csv')

df = pd.read_csv('dataset_gabungan.csv', encoding='utf-8')

print(f"Total rows: {len(df)}")
print(f"Label distribution:\n{df['label'].value_counts()}")

# Cleaning
df["text"] = df["text"].astype(str).map(clean_text)
df = df[(df["text"] != "") & (df["label"].isin([0, 1]))].copy()
df = df.drop_duplicates(subset=["text"]).reset_index(drop=True)

print(f"\nSetelah cleaning: {len(df)} rows")
print(f"Label distribution:\n{df['label'].value_counts()}")

X = df["text"].tolist()
y = df["label"].astype(int).values

X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.15, stratify=y, random_state=42
)

print(f"\nTrain: {len(X_train)} | Val: {len(X_val)}")

# ============================================================
# CELL 4: Tokenization
# ============================================================
MAX_VOCAB = 50000
MAX_LEN = 150

tok = Tokenizer(num_words=MAX_VOCAB, oov_token="<unk>")
tok.fit_on_texts(X_train)

def to_seq(texts):
    return pad_sequences(tok.texts_to_sequences(texts), maxlen=MAX_LEN)

Xtr = to_seq(X_train)
Xva = to_seq(X_val)

vocab_size = min(MAX_VOCAB, len(tok.word_index) + 1)
print(f"Vocab size: {vocab_size}")

# ============================================================
# CELL 5: Build & Train Model
# ============================================================
model = build_mkcnn(
    vocab_size=vocab_size,
    embed_dim=100,
    max_len=MAX_LEN,
    filters=128,
    kernels=(2, 3, 4, 5),
    dropout=0.3,
)

print(model.summary())

cb = [
    tf.keras.callbacks.ModelCheckpoint(
        "mkcnn_best.keras",
        monitor="val_accuracy",
        save_best_only=True,
        save_weights_only=False,
        verbose=1
    ),
    tf.keras.callbacks.EarlyStopping(
        monitor="val_accuracy",
        patience=3,
        restore_best_weights=True,
        verbose=1
    ),
]

history = model.fit(
    Xtr, y_train,
    validation_data=(Xva, y_val),
    epochs=6,
    batch_size=64,
    callbacks=cb,
    verbose=2,
)

# ============================================================
# CELL 6: Evaluation dengan Berbagai Threshold
# ============================================================
pred_proba = model.predict(Xva, verbose=0).ravel()

thresholds = [0.35, 0.40, 0.45, 0.50]

for tau in thresholds:
    pred = (pred_proba >= tau).astype(int)
    print(f"\n{'='*60}")
    print(f"Threshold = {tau:.2f}")
    print('='*60)
    print(classification_report(y_val, pred, digits=4, target_names=["VALID", "HOAKS"]))

    cm = confusion_matrix(y_val, pred)
    print(f"\nConfusion Matrix:")
    print(f"  TN={cm[0,0]:4d}  FP={cm[0,1]:4d}")
    print(f"  FN={cm[1,0]:4d}  TP={cm[1,1]:4d}")

# ============================================================
# CELL 7: Save Model & Tokenizer
# ============================================================
model.save("multi_kernel_model.h5", include_optimizer=False)
print("✅ Model saved: multi_kernel_model.h5")

with open("tokenizer.pkl", "wb") as f:
    pickle.dump(
        {"tokenizer": tok, "max_len": MAX_LEN, "max_vocab": MAX_VOCAB},
        f,
    )
print("✅ Tokenizer saved: tokenizer.pkl")

# Download files
from google.colab import files
files.download("multi_kernel_model.h5")
files.download("tokenizer.pkl")

print("\n✅ SELESAI! Download 2 file dan copy ke:")
print("   apps/api/app/assets/multi_kernel_model.h5")
print("   apps/api/app/assets/tokenizer.pkl")
```

### 3. Upload Dataset

- Klik ikon folder di sidebar kiri Colab
- Upload file `dataset_gabungan.csv`

### 4. Run All Cells

- Menu: Runtime > Run all
- Tunggu ~5-10 menit (dengan GPU lebih cepat)

### 5. Download Model

- Setelah selesai, file `multi_kernel_model.h5` dan `tokenizer.pkl` akan otomatis terdownload
- Copy ke folder: `apps/api/app/assets/`

### 6. Restart API & Test

```powershell
cd apps/api
python -m uvicorn app.main:app --reload
```

Lalu test:

```powershell
python test_prediction.py
```

## Mengapa Colab?

- ✅ Gratis
- ✅ GPU gratis (training lebih cepat)
- ✅ Tidak butuh disk space lokal
- ✅ Environment sudah ter-setup

## Alternative: Bersihkan Disk Lokal

```powershell
# Hapus cache pip
.\.venv\Scripts\python.exe -m pip cache purge

# Bersihkan temp Windows
cleanmgr /d C:

# Uninstall program tidak terpakai
# Pindahkan file besar ke drive lain
```
