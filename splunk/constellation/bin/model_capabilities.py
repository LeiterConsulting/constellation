"""Fail-closed modality checks backed by exact documented model IDs."""
import base64
import binascii
import re
from provider_service import ProviderError

# Availability from /models is not evidence of input modality support.
VISION_MODELS = {
    'gpt-6-luna': 'https://developers.openai.com/api/docs/models/gpt-6-luna',
    'gpt-6-astra': 'https://developers.openai.com/api/docs/guides/images-vision',
}
MAX_FILE_BYTES = 4_000_000


def capabilities(model):
    return {'images': model in VISION_MODELS, 'pdf': model in VISION_MODELS,
            'source': VISION_MODELS.get(model, ''), 'checkedOn': '2026-10-23',
            'reason': '' if model in VISION_MODELS else 'Image and PDF support is not verified for this exact model ID.'}


def attachment_parts(attachments, model, verified=None):
    if not isinstance(attachments, list) or len(attachments) > 2:
        raise ProviderError('Attach at most two images or PDFs per turn.')
    supported = verified if verified is not None else capabilities(model)
    if attachments and not (supported.get('images') or supported.get('pdf')):
        raise ProviderError('Attachments were not sent. Input support is not verified for this provider route and model.', 409)
    parts = []
    total = 0
    for attachment in attachments:
        if not isinstance(attachment, dict):
            raise ProviderError('The attachment is invalid.')
        name, data = attachment.get('name'), attachment.get('data')
        if not isinstance(name, str) or not 1 <= len(name) <= 200 or not isinstance(data, str):
            raise ProviderError('The attachment name or data is invalid.')
        match = re.fullmatch(r'data:(image/png|image/jpeg|image/webp|application/pdf);base64,([A-Za-z0-9+/=]+)', data)
        if not match or len(data) > 5_400_100:
            raise ProviderError('Attach a PNG, JPEG, WebP, or PDF under 4 MB.')
        mime = match.group(1)
        if not supported.get('pdf' if mime == 'application/pdf' else 'images'):
            raise ProviderError('Attachments were not sent. This provider route and selected model do not have verified support for this file type.', 409)
        try:
            raw = base64.b64decode(match.group(2), validate=True)
        except (ValueError, binascii.Error):
            raise ProviderError('The attachment encoding is invalid.') from None
        total += len(raw)
        valid = ((mime == 'image/png' and raw.startswith(b'\x89PNG\r\n\x1a\n'))
                 or (mime == 'image/jpeg' and raw.startswith(b'\xff\xd8\xff'))
                 or (mime == 'image/webp' and raw.startswith(b'RIFF') and raw[8:12] == b'WEBP')
                 or (mime == 'application/pdf' and raw.startswith(b'%PDF-')))
        if not valid or len(raw) > MAX_FILE_BYTES or total > 8_000_000:
            raise ProviderError('The attachment contents do not match an allowed file under 4 MB.')
        if mime == 'application/pdf':
            parts.append({'type': 'input_file', 'filename': 'reference.pdf', 'file_data': data})
        else:
            parts.append({'type': 'input_image', 'image_url': data, 'detail': 'high'})
    return parts
