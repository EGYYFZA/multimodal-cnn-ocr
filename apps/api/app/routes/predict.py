from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from app.services.config import settings
from app.services.preprocess import merge_inputs, clean_text
from app.services.model_service import predict_proba, decide_label, model_info, get_confidence_level
from app.services.dataset_service import search_similar, dataset_stats
from app.services.ocr_service import ocr_image_bytes, ocr_video_bytes
from app.services.log_service import append_log

router = APIRouter()

@router.get("/health")
def health():
    return {"ok": True, "model": model_info()}

@router.get("/dataset")
def dataset():
    return dataset_stats()

@router.post("/predict")
async def predict(
    title: str = Form(""),
    body: str = Form(""),
    image_file: UploadFile | None = File(None),
    video_file: UploadFile | None = File(None),
):
    title = (title or "").strip()
    body = (body or "").strip()

    if len(title) + len(body) > settings.max_text_chars:
        raise HTTPException(status_code=413, detail=f"Teks terlalu panjang (max {settings.max_text_chars} karakter).")

    ocr_chunks = []
    ocr_meta = []
    used_ocr = False

    # ---- OCR Image ----
    if image_file is not None:
        img_bytes = await image_file.read(settings.max_upload_mb * 1024 * 1024 + 1)
        if len(img_bytes) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"Gambar terlalu besar (max {settings.max_upload_mb} MB).")

        t = ocr_image_bytes(img_bytes)
        if t.strip():
            ocr_chunks.append(t)
            used_ocr = True
        ocr_meta.append({"type": "image", "chars": len(t or "")})

    # ---- OCR video ----
    if video_file is not None:
        vid_bytes = await video_file.read(settings.max_upload_mb * 1024 * 1024 + 1)
        if len(vid_bytes) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"Video terlalu besar (max {settings.max_upload_mb} MB).")

        print(f"[PREDICT] Processing video: {len(vid_bytes)} bytes")
        t, frames_used = ocr_video_bytes(vid_bytes)
        print(f"[PREDICT] Video OCR result: {len(t)} chars from {frames_used} frames")
        
        if t.strip():
            ocr_chunks.append(t)
            used_ocr = True
        ocr_meta.append({"type": "video", "frames_used": int(frames_used), "chars": len(t or "")})

    ocr_text = "\n".join([c for c in ocr_chunks if c.strip()]).strip()
    final_text = merge_inputs(title, body, ocr_text)

    # ---- Jika benar-benar kosong: jangan error 400, tapi response NO_TEXT ----
    if not final_text.strip():
        msg = (
            "Input kosong: OCR tidak menemukan teks pada media.\n"
            "- Pastikan gambar/video memang berisi teks yang jelas (tidak blur/gelap).\n"
            "- Untuk video: coba upload cuplikan yang ada teksnya (mis. screenshot frame).\n"
            "- Atau masukkan judul/isi berita sebagai teks."
        )
        try:
            append_log({
                "label": "NO_TEXT",
                "prob_hoax": "",
                "tau": "",
                "used_ocr": int(used_ocr),
                "ocr_type": ",".join([m["type"] for m in ocr_meta]) if ocr_meta else "",
                "title_len": len(title),
                "body_len": len(body),
                "ocr_len": len(ocr_text),
                "text_len": 0,
            })
        except Exception:
            pass

        return JSONResponse({
            "label": "NO_TEXT",
            "message": msg,
            "used_ocr": used_ocr,
            "ocr_meta": ocr_meta,
            "ocr_snippet": (ocr_text[:240] + "…") if len(ocr_text) > 240 else ocr_text,
            "evidence": [],
        })

    # ========== 1) Evidence untuk referensi dan fallback untuk teks pendek ==========
    # Untuk teks pendek, turunkan min_score agar bisa dapat evidence
    from app.services.preprocess import clean_text
    cleaned_length = len(clean_text(final_text))
    
    # Khusus OCR: threshold lebih tinggi karena banyak noise
    # Input manual: < 50 chars = short
    # Input OCR/Video: < 300 chars = short (NAIK dari 150 karena video sering punya teks lebih banyak)
    if used_ocr:
        is_short_text = cleaned_length < 300  # DIPERLUAS untuk video (was 150)
        min_score_threshold = 0.03  # TURUN untuk lebih permissive (was 0.05)
        print(f"[PREDICT] OCR detected: cleaned_length={cleaned_length}, is_short={is_short_text}, min_score={min_score_threshold}")
    else:
        is_short_text = cleaned_length < 50
        min_score_threshold = 0.08 if is_short_text else 0.15
    
    evidence = search_similar(final_text, top_k=5, min_score=min_score_threshold)

    # ========== 2) Probabilitas dari Multi-Kernel CNN Model ==========
    prob_hoax = predict_proba(final_text, padding="post", truncating="post")
    
    if used_ocr:
        dampening = 0.6  
        prob_hoax = 0.5 + (prob_hoax - 0.5) * dampening
        print(f"[PREDICT] OCR probability dampened: {prob_hoax:.6f} (dampening factor: {dampening})")

    info = model_info()
    output_mode = info.get("output_mode", "unknown")

    # threshold konsisten
    if output_mode == "softmax2":
        tau = 0.5
        threshold_used = 0.5
    else:
        tau = float(settings.operating_tau)
        threshold_used = tau

    # ========== 3) Label dari model dengan HYBRID DECISION untuk teks pendek ==========
    label = decide_label(prob_hoax, tau)
    confidence = get_confidence_level(prob_hoax, tau)
    prob_valid = max(0.0, min(1.0, 1.0 - float(prob_hoax)))
    
    # HYBRID DECISION: Untuk teks pendek ATAU video OCR, gunakan evidence sebagai second opinion
    has_evidence = len(evidence) >= 1  # Minimal 1 evidence dengan score > min_threshold
    
    decision_mode = "CNN"  # Default: pure CNN
    
    # CRITICAL: Video OCR SELALU gunakan hybrid jika ada evidence (reliability rendah)
    # Teks pendek manual juga gunakan hybrid
    should_use_hybrid = (is_short_text and has_evidence) or (used_ocr and has_evidence)
    
    if should_use_hybrid:
        # Count evidence labels (voting dari dataset)
        hoax_count = sum(1 for e in evidence if str(e.get("label_dataset", "")).lower() in ["1", "hoax", "hoaks"])
        valid_count = sum(1 for e in evidence if str(e.get("label_dataset", "")).lower() in ["0", "valid", "benar"])
        
        # PRIORITAS TERTINGGI: Evidence pertama (paling mirip) sebagai sinyal kuat
        top_evidence_label = None
        if evidence:
            top_label_str = str(evidence[0].get("label_dataset", "")).lower()
            if top_label_str in ["1", "hoax", "hoaks"]:
                top_evidence_label = "HOAKS"
            elif top_label_str in ["0", "valid", "benar"]:
                top_evidence_label = "VALID"
        
        # DEBUG LOG untuk troubleshooting
        print(f"[HYBRID DEBUG] used_ocr={used_ocr}, is_short={is_short_text}, CNN label: {label}, Top evidence: {top_evidence_label}, Hoax:{hoax_count}, Valid:{valid_count}")
        
        evidence_suggests_hoax = hoax_count > valid_count
        evidence_suggests_valid = valid_count > hoax_count
        
        # CRITICAL: Untuk teks pendek/OCR, CNN tidak reliable!
        # Strategi: Jika evidence pertama bertentangan dengan CNN, LANGSUNG override
        # Atau jika majority evidence bertentangan dengan CNN
        min_evidence_required = 1 if used_ocr else 2
        
        # Cek jika evidence pertama bertentangan dengan CNN (sinyal paling kuat!)
        top_disagrees = top_evidence_label and top_evidence_label != label
        
        print(f"[HYBRID DEBUG] top_disagrees: {top_disagrees}, min_evidence_required: {min_evidence_required}, will_override: {top_disagrees}")
        
        if top_disagrees and top_evidence_label == "HOAKS":
            # Evidence teratas (paling mirip) = HOAX, tapi CNN bilang VALID → OVERRIDE!
            label = "HOAKS"
            prob_hoax = 0.55 + (hoax_count * 0.05)  # Base 0.55 + bonus per evidence
            prob_valid = 1.0 - prob_hoax
            decision_mode = "HYBRID-EVIDENCE"
        
        elif top_disagrees and top_evidence_label == "VALID":
            # Evidence teratas = VALID, tapi CNN bilang HOAX → OVERRIDE!
            label = "VALID"
            prob_hoax = 0.45 - (valid_count * 0.05)  # Base 0.45 - penalty per evidence
            prob_valid = 1.0 - prob_hoax
            decision_mode = "HYBRID-EVIDENCE"
        
        elif evidence_suggests_hoax and label == "VALID" and hoax_count >= min_evidence_required:
            # Fallback: Majority evidence mengatakan HOAX, override CNN
            label = "HOAKS"
            prob_hoax = 0.55 + (hoax_count * 0.05)
            prob_valid = 1.0 - prob_hoax
            decision_mode = "HYBRID-EVIDENCE"
        
        elif evidence_suggests_valid and label == "HOAKS" and valid_count >= min_evidence_required:
            # Fallback: Majority evidence mengatakan VALID, override CNN
            label = "VALID"
            prob_hoax = 0.45 - (valid_count * 0.05)
            prob_valid = 1.0 - prob_hoax
            decision_mode = "HYBRID-EVIDENCE"
        
        # FINAL FALLBACK: Video OCR dengan minimal 1 evidence - gunakan evidence #1
        elif used_ocr and top_evidence_label is not None:
            top_label = top_evidence_label
            
            print(f"[VIDEO FALLBACK] No strong majority, using top evidence: {top_label} (was: {label})")
            
            if top_label != label:
                original_label = label
                label = top_label
                
                if top_label == "HOAKS":
                    prob_hoax = 0.60
                    prob_valid = 0.40
                else:
                    prob_hoax = 0.40
                    prob_valid = 0.60
                
                decision_mode = "HYBRID-FALLBACK"
                print(f"[VIDEO FALLBACK] Override {original_label} → {label}")
        else:
            # Model dan evidence agree atau evidence tidak decisive
            pass

    # logging
    try:
        append_log({
            "label": label,
            "prob_hoax": f"{prob_hoax:.6f}",
            "tau": f"{tau:.3f}",
            "used_ocr": int(used_ocr),
            "ocr_type": ",".join([m["type"] for m in ocr_meta]) if ocr_meta else "",
            "title_len": len(title),
            "body_len": len(body),
            "ocr_len": len(ocr_text),
            "text_len": len(final_text),
            "cleaned_len": cleaned_length,
            "decision_mode": decision_mode,
        })
    except Exception:
        pass

    response_data = {
        # UI: Label decision dengan hybrid system
        "label": label,
        "prob_hoax": float(prob_hoax),
        "prob_valid": float(prob_valid),

        "tau": float(tau),
        "threshold_used": float(threshold_used),
        "output_mode": output_mode,
        "confidence": confidence,

        "used_ocr": used_ocr,
        "ocr_meta": ocr_meta,
        "ocr_snippet": (ocr_text[:240] + "…") if len(ocr_text) > 240 else ocr_text,
        "mode": decision_mode,  
        "evidence": evidence,
        
        "text_length": {
            "original": len(final_text),
            "cleaned": cleaned_length,
            "is_short": is_short_text,
        },
    }
    
    return JSONResponse(response_data)
