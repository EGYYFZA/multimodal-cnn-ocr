# PSEUDOCODE IMPLEMENTASI SISTEM DETEKSI HOAX

## 1. IMPLEMENTASI MODUL OCR (TESSERACT)

### 1.1 Inisialisasi OCR Service

```pseudocode
CLASS OCRService:
    CONSTRUCTOR():
        SET tesseract_path = "path/to/Tesseract-OCR/tesseract.exe"
        SET tessdata_path = "path/to/Tesseract-OCR/tessdata"
        CONFIGURE pytesseract.tesseract_cmd = tesseract_path
        SET language_config = "ind+eng"  // Indonesian + English
        SET ocr_config = "--oem 3 --psm 6"  // LSTM OCR Engine Mode, Uniform text block
    END CONSTRUCTOR
```

### 1.2 Preprocessing Gambar untuk OCR

```pseudocode
FUNCTION preprocess_image_for_ocr(image_data):
    INPUT: image_data (binary atau path file)
    OUTPUT: preprocessed_image (numpy array)

    BEGIN
        // Baca gambar
        IF image_data is binary:
            image = READ image from bytes using PIL
        ELSE:
            image = READ image from file path
        END IF

        // Konversi ke grayscale
        gray_image = CONVERT image to grayscale using cv2.cvtColor

        // Denoising untuk menghilangkan noise
        denoised_image = APPLY cv2.fastNlMeansDenoising(gray_image)

        // Thresholding adaptif untuk meningkatkan kontras
        threshold_image = APPLY cv2.adaptiveThreshold(
            denoised_image,
            maxValue=255,
            adaptiveMethod=ADAPTIVE_THRESH_GAUSSIAN_C,
            thresholdType=THRESH_BINARY,
            blockSize=11,
            C=2
        )

        // Morphological operations untuk membersihkan noise kecil
        kernel = CREATE structuring element (3x3)
        cleaned_image = APPLY cv2.morphologyEx(threshold_image, MORPH_CLOSE, kernel)

        // Resize jika terlalu kecil (meningkatkan akurasi OCR)
        height, width = GET cleaned_image dimensions
        IF height < 300 OR width < 300:
            scale_factor = CALCULATE scale to reach min 300px
            cleaned_image = RESIZE image with scale_factor using INTER_CUBIC
        END IF

        RETURN cleaned_image
    END
END FUNCTION
```

### 1.3 Ekstraksi Teks dengan Tesseract

```pseudocode
FUNCTION extract_text_from_image(preprocessed_image):
    INPUT: preprocessed_image (numpy array)
    OUTPUT: extracted_text (string)

    BEGIN
        TRY:
            // Konfigurasi Tesseract
            custom_config = "--oem 3 --psm 6 -l ind+eng"

            // Ekstraksi teks menggunakan pytesseract
            text = CALL pytesseract.image_to_string(
                preprocessed_image,
                config=custom_config
            )

            // Post-processing teks
            cleaned_text = REMOVE excessive whitespaces from text
            cleaned_text = REMOVE special characters (keep alphanumeric and basic punctuation)
            cleaned_text = CONVERT to lowercase
            cleaned_text = STRIP leading/trailing spaces

            // Validasi hasil
            IF LENGTH(cleaned_text) < 10:
                RETURN "Text too short or OCR failed"
            END IF

            RETURN cleaned_text

        CATCH Exception as e:
            LOG error message
            RETURN empty string or error message
        END TRY
    END
END FUNCTION
```

### 1.4 Pipeline OCR Lengkap

```pseudocode
FUNCTION perform_ocr(image_input):
    INPUT: image_input (file path, binary data, atau PIL Image)
    OUTPUT: extracted_text (string)

    BEGIN
        // Validasi input
        IF image_input is empty OR invalid:
            RETURN error "Invalid image input"
        END IF

        // Preprocessing
        preprocessed_image = CALL preprocess_image_for_ocr(image_input)

        // Ekstraksi teks
        extracted_text = CALL extract_text_from_image(preprocessed_image)

        // Validasi hasil
        IF extracted_text is empty OR LENGTH(extracted_text) < 5:
            // Coba dengan konfigurasi alternatif
            custom_config = "--oem 3 --psm 3 -l ind+eng"  // PSM 3: Fully automatic page segmentation
            extracted_text = CALL pytesseract.image_to_string(
                preprocessed_image,
                config=custom_config
            )
        END IF

        RETURN extracted_text
    END
END FUNCTION
```

---

## 2. IMPLEMENTASI MODUL KLASIFIKASI (MULTI KERNEL 1D-CNN)

### 2.1 Arsitektur Model Multi Kernel 1D-CNN

```pseudocode
FUNCTION build_multi_kernel_cnn_model(vocab_size, embedding_dim, max_length):
    INPUT:
        - vocab_size: ukuran vocabulary
        - embedding_dim: dimensi embedding (contoh: 128)
        - max_length: panjang maksimal sequence (contoh: 500)
    OUTPUT: compiled_model (Keras Model)

    BEGIN
        // Layer Input
        input_layer = CREATE Input(shape=(max_length,))

        // Embedding Layer
        embedding_layer = CREATE Embedding(
            input_dim=vocab_size,
            output_dim=embedding_dim,
            input_length=max_length,
            trainable=True
        )
        embedded = APPLY embedding_layer to input_layer

        // Multi-Kernel Convolution Branches
        // Kernel Size 3
        conv1 = CREATE Conv1D(filters=128, kernel_size=3, activation='relu')
        conv1_output = APPLY conv1 to embedded
        pool1 = APPLY GlobalMaxPooling1D() to conv1_output

        // Kernel Size 4
        conv2 = CREATE Conv1D(filters=128, kernel_size=4, activation='relu')
        conv2_output = APPLY conv2 to embedded
        pool2 = APPLY GlobalMaxPooling1D() to conv2_output

        // Kernel Size 5
        conv3 = CREATE Conv1D(filters=128, kernel_size=5, activation='relu')
        conv3_output = APPLY conv3 to embedded
        pool3 = APPLY GlobalMaxPooling1D() to conv3_output

        // Concatenate semua kernel outputs
        concatenated = CONCATENATE([pool1, pool2, pool3])

        // Dropout untuk regularisasi
        dropout1 = APPLY Dropout(rate=0.5) to concatenated

        // Dense Layers
        dense1 = CREATE Dense(units=128, activation='relu')
        dense1_output = APPLY dense1 to dropout1

        dropout2 = APPLY Dropout(rate=0.3) to dense1_output

        // Output Layer (Binary Classification)
        output_layer = CREATE Dense(units=1, activation='sigmoid')
        output = APPLY output_layer to dropout2

        // Build Model
        model = CREATE Model(inputs=input_layer, outputs=output)

        // Compile Model
        COMPILE model with:
            optimizer='adam'
            loss='binary_crossentropy'
            metrics=['accuracy', 'precision', 'recall']

        RETURN model
    END
END FUNCTION
```

### 2.2 Preprocessing Teks untuk Model

```pseudocode
FUNCTION preprocess_text_for_model(text):
    INPUT: text (string)
    OUTPUT: preprocessed_text (string)

    BEGIN
        // Lowercase
        text = CONVERT text to lowercase

        // Hapus URL
        text = REMOVE pattern "http[s]?://\S+" from text

        // Hapus mention dan hashtag
        text = REMOVE pattern "@\w+" from text
        text = REMOVE pattern "#\w+" from text

        // Hapus angka
        text = REMOVE pattern "\d+" from text

        // Hapus karakter non-alfabet (kecuali spasi)
        text = REMOVE pattern "[^a-z\s]" from text

        // Hapus whitespace berlebih
        text = REMOVE excessive whitespaces
        text = STRIP leading/trailing spaces

        // Tokenisasi kata (opsional, tergantung kebutuhan)
        // tokens = SPLIT text by whitespace

        // Stopword removal (opsional)
        // stopwords = LOAD Indonesian stopwords
        // tokens = FILTER tokens that not in stopwords
        // text = JOIN tokens with space

        RETURN text
    END
END FUNCTION
```

### 2.3 Tokenisasi dan Padding

```pseudocode
FUNCTION tokenize_and_pad(texts, tokenizer, max_length):
    INPUT:
        - texts: list of strings
        - tokenizer: Keras Tokenizer object
        - max_length: maximum sequence length
    OUTPUT: padded_sequences (numpy array)

    BEGIN
        // Tokenize teks menjadi sequence of integers
        sequences = CALL tokenizer.texts_to_sequences(texts)

        // Padding sequences ke panjang yang sama
        padded_sequences = APPLY pad_sequences(
            sequences,
            maxlen=max_length,
            padding='post',  // padding di akhir
            truncating='post'  // truncate di akhir jika terlalu panjang
        )

        RETURN padded_sequences
    END
END FUNCTION
```

### 2.4 Load Model dan Prediksi

```pseudocode
FUNCTION load_model_and_predict(text, model_path, tokenizer, max_length):
    INPUT:
        - text: string teks untuk diprediksi
        - model_path: path ke file model .h5
        - tokenizer: Keras Tokenizer object
        - max_length: panjang maksimal sequence
    OUTPUT: prediction_result (dict)

    BEGIN
        // Load model
        model = LOAD model from model_path using load_model()

        // Preprocess teks
        preprocessed_text = CALL preprocess_text_for_model(text)

        // Tokenize dan padding
        sequences = CALL tokenizer.texts_to_sequences([preprocessed_text])
        padded = APPLY pad_sequences(sequences, maxlen=max_length, padding='post')

        // Prediksi
        prediction_prob = CALL model.predict(padded)[0][0]

        // Tentukan label berdasarkan threshold (0.5)
        IF prediction_prob >= 0.5:
            label = "HOAX"
            confidence = prediction_prob
        ELSE:
            label = "VALID"
            confidence = 1 - prediction_prob
        END IF

        // Format hasil
        result = {
            "label": label,
            "confidence": confidence,
            "probability_hoax": prediction_prob,
            "probability_valid": 1 - prediction_prob
        }

        RETURN result
    END
END FUNCTION
```

### 2.5 Training Model (Opsional - untuk referensi)

```pseudocode
FUNCTION train_multi_kernel_model(X_train, y_train, X_val, y_val):
    INPUT:
        - X_train: training sequences (padded)
        - y_train: training labels
        - X_val: validation sequences (padded)
        - y_val: validation labels
    OUTPUT: trained_model, history

    BEGIN
        // Build model
        model = CALL build_multi_kernel_cnn_model(
            vocab_size=10000,
            embedding_dim=128,
            max_length=500
        )

        // Callbacks
        early_stopping = CREATE EarlyStopping(
            monitor='val_loss',
            patience=5,
            restore_best_weights=True
        )

        model_checkpoint = CREATE ModelCheckpoint(
            filepath='best_model.h5',
            monitor='val_accuracy',
            save_best_only=True
        )

        reduce_lr = CREATE ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=3
        )

        // Training
        history = CALL model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=50,
            batch_size=32,
            callbacks=[early_stopping, model_checkpoint, reduce_lr],
            verbose=1
        )

        RETURN model, history
    END
END FUNCTION
```

---

## 3. INTEGRASI OCR DAN MODEL MULTI KERNEL 1D-CNN

### 3.1 Sistem Prediksi Terintegrasi

```pseudocode
FUNCTION integrated_hoax_detection(input_data, input_type):
    INPUT:
        - input_data: bisa berupa image atau text
        - input_type: "image" atau "text"
    OUTPUT: prediction_result (dict)

    BEGIN
        // Inisialisasi services
        ocr_service = CREATE OCRService()
        model_service = CREATE ModelService()

        // Tentukan teks untuk diproses
        IF input_type == "image":
            // OCR Pipeline
            extracted_text = CALL ocr_service.perform_ocr(input_data)

            // Validasi hasil OCR
            IF extracted_text is empty OR LENGTH(extracted_text) < 10:
                RETURN {
                    "status": "error",
                    "message": "Failed to extract text from image or text too short",
                    "extracted_text": extracted_text
                }
            END IF

            text_to_classify = extracted_text

        ELSE IF input_type == "text":
            text_to_classify = input_data

        ELSE:
            RETURN error "Invalid input type"
        END IF

        // Model Prediction Pipeline
        prediction = CALL model_service.predict(text_to_classify)

        // Compile hasil
        result = {
            "status": "success",
            "input_type": input_type,
            "text_analyzed": text_to_classify,
            "prediction": prediction["label"],
            "confidence": prediction["confidence"],
            "probability_hoax": prediction["probability_hoax"],
            "probability_valid": prediction["probability_valid"],
            "timestamp": CURRENT_TIMESTAMP()
        }

        IF input_type == "image":
            result["extracted_text"] = extracted_text
        END IF

        // Log hasil prediksi
        CALL log_prediction(result)

        RETURN result
    END
END FUNCTION
```

### 3.2 API Endpoint Handler

```pseudocode
FUNCTION handle_prediction_request(request):
    INPUT: HTTP request object
    OUTPUT: JSON response

    BEGIN
        TRY:
            // Parse request
            IF request contains file (image):
                file = GET file from request
                file_bytes = READ file as bytes

                // Validasi file
                IF NOT is_valid_image(file):
                    RETURN error_response("Invalid image format")
                END IF

                // Process image
                result = CALL integrated_hoax_detection(
                    input_data=file_bytes,
                    input_type="image"
                )

            ELSE IF request contains text:
                text = GET text from request.form or request.json

                // Validasi text
                IF text is empty OR LENGTH(text) < 10:
                    RETURN error_response("Text too short (minimum 10 characters)")
                END IF

                // Process text
                result = CALL integrated_hoax_detection(
                    input_data=text,
                    input_type="text"
                )

            ELSE:
                RETURN error_response("No valid input provided")
            END IF

            // Return success response
            RETURN json_response(result, status_code=200)

        CATCH Exception as e:
            LOG error details
            RETURN error_response(
                message="An error occurred during prediction",
                error_details=str(e),
                status_code=500
            )
        END TRY
    END
END FUNCTION
```

### 3.3 Batch Processing (untuk multiple images/texts)

```pseudocode
FUNCTION batch_hoax_detection(inputs, input_type):
    INPUT:
        - inputs: list of images or texts
        - input_type: "image" atau "text"
    OUTPUT: list of prediction results

    BEGIN
        results = CREATE empty list

        FOR each input_data IN inputs:
            TRY:
                // Process individual input
                result = CALL integrated_hoax_detection(input_data, input_type)
                APPEND result to results

            CATCH Exception as e:
                // Handle error gracefully
                error_result = {
                    "status": "error",
                    "message": str(e),
                    "input_index": INDEX of input_data
                }
                APPEND error_result to results
            END TRY
        END FOR

        // Generate summary
        summary = {
            "total_processed": LENGTH(inputs),
            "successful": COUNT results where status == "success",
            "failed": COUNT results where status == "error",
            "hoax_detected": COUNT results where prediction == "HOAX",
            "valid_detected": COUNT results where prediction == "VALID"
        }

        RETURN {
            "summary": summary,
            "results": results
        }
    END
END FUNCTION
```

### 3.4 Pipeline Lengkap dengan Caching dan Optimasi

```pseudocode
FUNCTION optimized_prediction_pipeline(input_data, input_type, use_cache=True):
    INPUT:
        - input_data: image atau text
        - input_type: "image" atau "text"
        - use_cache: boolean untuk enable/disable caching
    OUTPUT: prediction result

    BEGIN
        // Generate hash untuk caching
        IF use_cache:
            input_hash = CALCULATE MD5 hash of input_data

            // Check cache
            cached_result = GET from cache using input_hash
            IF cached_result exists:
                RETURN cached_result
            END IF
        END IF

        // Process input
        result = CALL integrated_hoax_detection(input_data, input_type)

        // Store in cache
        IF use_cache AND result["status"] == "success":
            STORE result in cache with key=input_hash, TTL=3600  // 1 hour
        END IF

        RETURN result
    END
END FUNCTION
```

### 3.5 Main Application Flow

```pseudocode
FUNCTION main_application():
    BEGIN
        // Initialize Flask/FastAPI application
        app = CREATE Flask application

        // Initialize services
        CALL initialize_services():
            - OCR Service with Tesseract configuration
            - Model Service with loaded model and tokenizer
            - Logging Service
            - Cache Service (Redis or in-memory)
        END CALL

        // Define routes
        ROUTE "/predict" METHOD POST:
            result = CALL handle_prediction_request(request)
            RETURN result
        END ROUTE

        ROUTE "/batch_predict" METHOD POST:
            results = CALL batch_hoax_detection(request.data, request.type)
            RETURN results
        END ROUTE

        ROUTE "/health" METHOD GET:
            RETURN {"status": "healthy", "services": service_status}
        END ROUTE

        // Start application
        START app on host="0.0.0.0", port=5000
    END
END FUNCTION
```

---

## 4. ALGORITMA DETAIL INTEGRASI

### 4.1 Flow Chart Sistem

```
START
  ↓
[Input Diterima]
  ↓
[Cek Tipe Input]
  ↓
  ├─→ [Image] → [Preprocessing Image] → [OCR Tesseract] → [Extract Text]
  │                                                              ↓
  └─→ [Text] ───────────────────────────────────────────────→ [Text Validated]
                                                                  ↓
                                                          [Preprocess Text]
                                                                  ↓
                                                          [Tokenize & Pad]
                                                                  ↓
                                                          [Multi-Kernel CNN]
                                                                  ↓
                                                          [Prediction Output]
                                                                  ↓
                                                          [Format Result]
                                                                  ↓
                                                          [Log & Return]
                                                                  ↓
                                                                 END
```

### 4.2 Error Handling Strategy

```pseudocode
FUNCTION robust_prediction_with_fallback(input_data, input_type):
    INPUT: input_data, input_type
    OUTPUT: prediction result with error handling

    BEGIN
        max_retries = 3
        retry_count = 0

        WHILE retry_count < max_retries:
            TRY:
                result = CALL integrated_hoax_detection(input_data, input_type)

                // Validasi hasil
                IF result["status"] == "success":
                    RETURN result
                END IF

            CATCH OCRException as e:
                // Try alternative OCR configuration
                LOG "OCR failed, trying alternative config"
                IF input_type == "image":
                    // Try with different PSM mode
                    result = CALL ocr_with_fallback_config(input_data)
                END IF

            CATCH ModelException as e:
                // Model prediction error
                LOG "Model prediction failed"
                RETURN {
                    "status": "error",
                    "message": "Model prediction failed",
                    "error": str(e)
                }

            CATCH Exception as e:
                LOG "Unexpected error: " + str(e)

            END TRY

            retry_count = retry_count + 1
            WAIT 1 second
        END WHILE

        // Final fallback
        RETURN {
            "status": "error",
            "message": "Failed after " + max_retries + " attempts"
        }
    END
END FUNCTION
```

---

## 5. KOMPLEKSITAS DAN PERFORMA

### Kompleksitas Waktu

- **OCR Processing**: O(W × H) dimana W = width, H = height gambar
- **Text Preprocessing**: O(n) dimana n = panjang teks
- **CNN Prediction**: O(L × K) dimana L = sequence length, K = jumlah kernels
- **Total Pipeline**: O(W × H + n + L × K)

### Optimisasi

1. **Image Resizing**: Resize gambar ke ukuran optimal sebelum OCR
2. **Batch Processing**: Process multiple inputs dalam satu forward pass
3. **Model Caching**: Load model sekali dan reuse untuk multiple predictions
4. **Result Caching**: Cache hasil prediksi untuk input yang sama
5. **Async Processing**: Gunakan async/await untuk I/O operations

---

## REFERENSI

- Tesseract OCR: https://github.com/tesseract-ocr/tesseract
- Keras/TensorFlow: https://www.tensorflow.org/
- CNN for Text Classification: Kim (2014) - "Convolutional Neural Networks for Sentence Classification"
