export async function compressImage(file, { maxDimension = 1280, quality = 0.85 } = {}) {
    if (!file || !file.type.startsWith("image/")) {
        return file;
    }

    const url = URL.createObjectURL(file);

    try {
        const img = new Image();
        img.src = url;
        await img.decode();

        let source = img;
        try {
            source = await createImageBitmap(img, { imageOrientation: "from-image" });
        } catch {
            // Fallback to the plain image if orientation handling is unsupported.
        }

        const { width, height } = source;
        const scale = Math.min(1, maxDimension / Math.max(width, height));
        const canvasWidth = Math.round(width * scale);
        const canvasHeight = Math.round(height * scale);

        const canvas = document.createElement("canvas");
        canvas.width = canvasWidth;
        canvas.height = canvasHeight;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(source, 0, 0, canvasWidth, canvasHeight);

        if (source !== img) {
            source.close();
        }

        const blob = await new Promise((resolve) => {
            canvas.toBlob((b) => resolve(b), "image/jpeg", quality);
        });

        return blob || file;
    } catch {
        return file;
    } finally {
        URL.revokeObjectURL(url);
    }
}
