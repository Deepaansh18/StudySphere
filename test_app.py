import io
import os
import unittest

from main import app


def make_pdf_bytes(text: str) -> bytes:
    escaped = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    content = f"BT /F1 12 Tf 50 80 Td ({escaped}) Tj ET"
    stream = f"<< /Length {len(content.encode('latin-1'))} >>\nstream\n{content}\nendstream"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        stream,
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\n{obj}\nendobj\n".encode('latin-1'))
    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode('latin-1'))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode('latin-1'))
    trailer = f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
    pdf.extend(trailer.encode('latin-1'))
    return bytes(pdf)


class StudySphereAppTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_main_flow(self):
        pdf_bytes = make_pdf_bytes(
            'Photosynthesis is the process by which plants convert sunlight into chemical energy. '
            'The key concept is chlorophyll absorbs light. Important definitions include ATP and glucose.'
        )
        response = self.client.post(
            '/api/analyze',
            data={'pdf': (io.BytesIO(pdf_bytes), 'lecture.pdf'), 'subject': 'Biology'},
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        self.assertIn('notes', payload)
        self.assertEqual(len(payload['notes']['quiz']), 5)

        ask_response = self.client.post(
            '/api/ask',
            json={'question': 'What is photosynthesis?', 'lecture_id': payload['lecture_id']}
        )
        self.assertEqual(ask_response.status_code, 200, ask_response.get_data(as_text=True))
        answer = ask_response.get_json()['answer']
        self.assertIn('photosynthesis', answer.lower())


if __name__ == '__main__':
    unittest.main()
