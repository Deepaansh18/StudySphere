const form = document.getElementById('upload-form');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('lecture-upload');
const fileBadge = document.getElementById('file-badge');
const generateBtn = document.getElementById('generate-btn');
const landingSection = document.getElementById('landing-section');
const processingSection = document.getElementById('processing-section');
const resultsSection = document.getElementById('results-section');
const notesContent = document.getElementById('notes-content');
const quizContent = document.getElementById('quiz-content');
const subjectInput = document.getElementById('subject-input');
const selectedSubject = document.getElementById('results-subject');
const askForm = document.getElementById('ask-form');
const askInput = document.getElementById('ask-input');
const chatWindow = document.getElementById('chat-window');
const exportBtn = document.getElementById('export-btn');
const suggestionButtons = document.querySelectorAll('.suggestion-btn');

let lectureId = null;
let quizState = [];

const toggleSectionVisibility = () => {
  landingSection.classList.add('hidden');
  processingSection.classList.remove('hidden');
  resultsSection.classList.add('hidden');
};

const showResults = () => {
  landingSection.classList.add('hidden');
  processingSection.classList.add('hidden');
  resultsSection.classList.remove('hidden');
};

const setProcessingStep = (stepIndex) => {
  const steps = document.querySelectorAll('.stream-step');
  steps.forEach((step, index) => {
    step.classList.toggle('active', index === stepIndex);
  });
};

const updateSelectedFile = (file) => {
  fileBadge.textContent = file ? file.name : 'No file selected';
  fileBadge.classList.toggle('hidden', !file);
};

fileInput.addEventListener('change', (event) => {
  const file = event.target.files[0];
  updateSelectedFile(file);
});

dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', (event) => {
  event.preventDefault();
  dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('dragover');
});
dropZone.addEventListener('drop', (event) => {
  event.preventDefault();
  const file = event.dataTransfer.files[0];
  if (file) {
    fileInput.files = event.dataTransfer.files;
    updateSelectedFile(file);
  }
  dropZone.classList.remove('dragover');
});

const renderNotes = (notes) => {
  const formatList = (items) => {
    if (!Array.isArray(items)) return `<p>${items || ''}</p>`;

    return `<ul>${items.map((item) => {
      if (typeof item === 'string') return `<li>${item}</li>`;
      if (item && typeof item === 'object') {
        if (item.concept || item.term) {
          const label = item.concept || item.term;
          const detail = item.explanation || item.definition || '';
          return `<li><strong>${label}</strong>: ${detail}</li>`;
        }
        return `<li>${JSON.stringify(item)}</li>`;
      }
      return `<li>${String(item)}</li>`;
    }).join('')}</ul>`;
  };

  const blocks = [
    { title: 'Overview', content: notes.overview },
    { title: 'Key Concepts', content: notes.key_concepts },
    { title: 'Important Definitions', content: notes.important_definitions },
    { title: 'Exam Points', content: notes.exam_points },
    { title: 'Quick Recap', content: notes.quick_recap }
  ];

  notesContent.innerHTML = blocks.map((block) => {
    const rendered = Array.isArray(block.content)
      ? formatList(block.content)
      : `<p>${block.content || ''}</p>`;

    return `
      <div class="note-block">
        <h3>${block.title}</h3>
        ${rendered}
      </div>
    `;
  }).join('');
};

const renderQuiz = (quiz) => {
  quizState = quiz.map((question, qIndex) => ({
    ...question,
    selectedOption: null,
    answered: false,
    questionIndex: qIndex
  }));

  if (!quiz || !quiz.length) {
    quizContent.innerHTML = '<p>No quiz available for this lecture.</p>';
    return;
  }

  quizContent.innerHTML = quizState.map((question, index) => `
    <div class="quiz-question" data-index="${index}">
      <h3>${index + 1}. ${question.question}</h3>
      <div class="quiz-options">
        ${question.options.map((option, optionIndex) => `
          <button type="button" class="option-btn" data-option="${option}" data-index="${index}">
            ${String.fromCharCode(65 + optionIndex)}. ${option}
          </button>
        `).join('')}
      </div>
      <div class="quiz-actions">
        <span class="score-pill">Score: ${calculateScore()}/${quizState.length}</span>
        <button type="button" class="primary-btn small-btn next-btn" data-next-index="${index}">Next</button>
      </div>
    </div>
  `).join('');

  attachQuizHandlers();
};

const calculateScore = () => {
  return quizState.filter((item) => item.selectedOption === item.correct_answer && item.answered).length;
};

const revealQuestionResult = (questionIndex) => {
  const question = quizState[questionIndex];
  const questionElement = document.querySelector(`.quiz-question[data-index="${questionIndex}"]`);

  if (!questionElement) return;

  const buttons = questionElement.querySelectorAll('.option-btn');
  buttons.forEach((button) => {
    const option = button.dataset.option;
    button.disabled = true;
    if (option === question.correct_answer) {
      button.classList.add('correct');
    }
    if (question.selectedOption === option && option !== question.correct_answer) {
      button.classList.add('incorrect');
    }
  });

  const selected = question.selectedOption;
  if (!selected) {
    const explanation = document.createElement('div');
    explanation.className = 'explanation-box';
    explanation.textContent = `Correct answer: ${question.correct_answer}. ${question.explanation}`;
    questionElement.appendChild(explanation);
    return;
  }

  const explanation = document.createElement('div');
  explanation.className = 'explanation-box';
  explanation.textContent = question.explanation;
  questionElement.appendChild(explanation);

  const nextButton = questionElement.querySelector('.next-btn');
  nextButton.textContent = questionIndex === quizState.length - 1 ? 'Finish' : 'Next';
};

const attachQuizHandlers = () => {
  const optionButtons = document.querySelectorAll('.option-btn');
  optionButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const index = Number(button.dataset.index);
      const question = quizState[index];
      if (!question || question.answered) return;

      question.selectedOption = button.dataset.option;
      question.answered = true;

      const parent = button.closest('.quiz-question');
      const allButtons = parent.querySelectorAll('.option-btn');
      allButtons.forEach((btn) => {
        btn.classList.toggle('selected', btn === button);
      });

      renderQuizState();
      revealQuestionResult(index);
    });
  });

  const nextButtons = document.querySelectorAll('.next-btn');
  nextButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const index = Number(button.dataset.nextIndex);
      const nextIndex = index + 1;
      const currentQuestion = quizState[index];

      if (!currentQuestion || !currentQuestion.answered) {
        revealQuestionResult(index);
        return;
      }

      const questionBlock = document.querySelector(`.quiz-question[data-index="${index}"]`);
      if (questionBlock) {
        questionBlock.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }

      if (nextIndex < quizState.length) {
        const nextBlock = document.querySelector(`.quiz-question[data-index="${nextIndex}"]`);
        if (nextBlock) {
          nextBlock.scrollIntoView({ behavior: 'smooth', block: 'center' });
          revealQuestionResult(index);
        }
      } else {
        revealQuestionResult(index);
        const score = quizState.filter((item) => item.selectedOption === item.correct_answer && item.answered).length;
        const summaryBox = document.createElement('div');
        summaryBox.className = 'explanation-box';
        summaryBox.textContent = `You scored ${score}/${quizState.length}. Review the explanations above and revisit the notes to prepare for the exam.`;
        quizContent.appendChild(summaryBox);
      }
    });
  });
};

const renderQuizState = () => {
  const scoreText = document.querySelectorAll('.score-pill');
  scoreText.forEach((pill) => {
    pill.textContent = `Score: ${calculateScore()}/${quizState.length}`;
  });
};

const addChatBubble = (role, message) => {
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = message;
  chatWindow.appendChild(bubble);
  chatWindow.scrollTop = chatWindow.scrollHeight;
};

const populateSuggestions = () => {
  suggestionButtons.forEach((button) => {
    button.addEventListener('click', () => {
      askInput.value = button.textContent;
      askInput.focus();
    });
  });
};

form.addEventListener('submit', async (event) => {
  event.preventDefault();

  if (!fileInput.files.length) {
    alert('Please upload a lecture PDF to continue.');
    return;
  }

  const file = fileInput.files[0];
  const subject = subjectInput.value.trim() || 'Lecture';

  toggleSectionVisibility();
  setProcessingStep(0);
  let step = 0;
  const stepTimer = setInterval(() => {
    step = (step + 1) % 4;
    setProcessingStep(step);
  }, 1000);

  const formData = new FormData();
  formData.append('pdf', file);
  formData.append('subject', subject);

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      body: formData,
    });

    const result = await response.json();
    clearInterval(stepTimer);

    if (!response.ok) {
      throw new Error(result.error || 'Could not analyze your lecture.');
    }

    lectureId = result.lecture_id;
    selectedSubject.textContent = result.subject || 'Lecture Revision';
    renderNotes(result.notes);
    renderQuiz(result.notes.quiz || []);
    showResults();
  } catch (error) {
    clearInterval(stepTimer);
    alert(error.message || 'Something went wrong while analyzing the lecture.');
    landingSection.classList.remove('hidden');
    processingSection.classList.add('hidden');
  }
});

askForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const question = askInput.value.trim();
  if (!question) return;

  addChatBubble('user', question);
  askInput.value = '';

  try {
    const response = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, lecture_id: lectureId })
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || 'Unable to answer this lecture question.');
    }

    addChatBubble('assistant', result.answer);
  } catch (error) {
    addChatBubble('assistant', error.message || 'I could not answer that based on the uploaded lecture.');
  }
});

exportBtn.addEventListener('click', () => {
  const notesText = notesContent.innerText;
  const quizText = quizContent.innerText;
  const exportContent = `StudySphere - ${selectedSubject.textContent}\n\nREVISION NOTES\n${notesText}\n\nQUIZ\n${quizText}`;
  const blob = new Blob([exportContent], { type: 'text/plain' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${selectedSubject.textContent || 'StudySphere'}-revision.txt`;
  link.click();
  URL.revokeObjectURL(link.href);
});

populateSuggestions();
