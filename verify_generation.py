import io
from main import app, extract_pdf_text

lecture_text = '''
Photosynthesis is the process by which green plants convert carbon dioxide and water into glucose and oxygen using light energy captured by chlorophyll.

During photosynthesis, chlorophyll absorbs light in the chloroplasts. The light-dependent reactions occur in the thylakoid membranes and produce ATP and NADPH. The Calvin cycle occurs in the stroma and uses carbon dioxide to build sugars.

The equation for photosynthesis is: carbon dioxide + water + light energy -> glucose + oxygen.

Cellular respiration is the process by which cells release energy from glucose. Glycolysis occurs in the cytoplasm, the Krebs cycle occurs in the mitochondria, and oxidative phosphorylation produces the most ATP.

A key comparison is that photosynthesis stores energy, while respiration releases it.

The professor is Dr. James Carter from Northbridge University. Course code BIO-201. Page 7 of 12.
'''

content = "BT /F1 12 Tf 50 80 Td (" + lecture_text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)') + ") Tj ET"
stream = "<< /Length %d >>\nstream\n%s\nendstream" % (len(content.encode('latin-1')), content)
objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 220] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
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

with app.test_client() as client:
    response = client.post(
        '/api/analyze',
        data={'pdf': (io.BytesIO(bytes(pdf)), 'lecture.pdf'), 'subject': 'Biology'},
        content_type='multipart/form-data'
    )
    payload = response.get_json()
    print('status', response.status_code)
    print('notes_title', payload['notes']['title'])
    print('overview', payload['notes']['overview'])
    print('key_concepts_count', len(payload['notes']['key_concepts']))
    print('definition_count', len(payload['notes']['important_definitions']))
    print('quiz_count', len(payload['notes']['quiz']))
    for i, q in enumerate(payload['notes']['quiz'][:3], 1):
        print(f'Q{i}: {q["question"]}')
        print('options:', q['options'])
        print('answer:', q['correct_answer'])
    ask = client.post('/api/ask', json={'question': 'What happens during photosynthesis?', 'lecture_id': payload['lecture_id']})
    print('ask_status', ask.status_code)
    print('ask_answer', ask.get_json()['answer'][:220])
