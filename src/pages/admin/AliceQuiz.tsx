/**
 * AliceQuiz — Employee quiz engine for Alice training points.
 *
 * Quiz data stored in Setting records:
 *   name = "alice-employee-qa-{topic}"
 *   config.questions[] = {
 *     ida: "212-1",              // {setting_id}-{seq} — stable, never changes
 *     uuid?: string,             // set when shared with Alice HQ
 *     seq?: number,              // display order (user can reorder, ida stays fixed)
 *     question: string,
 *     correct?: string,          // ida of correct answer (e.g. "212-1-2")
 *     explanation?: string,
 *     answers: [
 *       { ida: "212-1-1", answer: "fine" },
 *       { ida: "212-1-2", answer: "good" },
 *     ]
 *   }
 *
 * Responses stored in Setting records:
 *   name = "alice-employee-qa-response-{user_id}"
 *   config.responses[] = { question_ida, answer_ida, correct, dt }
 */
import { useCallback, useEffect, useState } from 'react';
import { getRecords, saveRecord } from '@/api/wcapi';
import { useAppSelector } from '@/store/hooks';

interface QuizAnswer {
  ida: string;       // "{setting_id}-{q_seq}-{a_seq}"
  answer: string;
}

interface QuizQuestion {
  ida: string;       // "{setting_id}-{seq}" — stable
  uuid?: string;
  seq?: number;
  question: string;
  answers: QuizAnswer[];
  correct?: string;  // ida of correct answer
  explanation?: string;
}

interface QuizSet {
  setting_id: number;
  topic: string;
  questions: QuizQuestion[];
}

interface QuizResponse {
  question_ida: string;
  answer_ida: string;
  correct: boolean;
  dt: string;
}

export default function AliceQuiz() {
  const { user } = useAppSelector((s) => s.auth);
  const [quizSets, setQuizSets] = useState<QuizSet[]>([]);
  const [selectedSet, setSelectedSet] = useState<QuizSet | null>(null);
  const [responses, setResponses] = useState<QuizResponse[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<'list' | 'take' | 'results'>('list');

  // Load quiz sets
  const loadQuizSets = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getRecords('setting', {
        name__startswith: 'alice-employee-qa-',
        limit: 100,
      });
      const sets: QuizSet[] = (res?.results || [])
        .filter((s: any) => !s.name.includes('-response-'))
        .filter((s: any) => s.config?.questions?.length > 0)
        .map((s: any) => ({
          setting_id: s.id,
          topic: s.name.replace('alice-employee-qa-', '').replace(/-/g, ' '),
          questions: (s.config.questions || [])
            .sort((a: any, b: any) => (a.seq || 0) - (b.seq || 0)),
        }));
      setQuizSets(sets);
    } catch (err) {
      console.error('[AliceQuiz] Failed to load quiz sets:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load user's prior responses
  const loadResponses = useCallback(async () => {
    if (!user?.id) return;
    try {
      const res = await getRecords('setting', {
        name: `alice-employee-qa-response-${user.id}`,
        limit: 1,
      });
      const rec = (res?.results || [])[0];
      setResponses(rec?.config?.responses || []);
    } catch { /* ignore */ }
  }, [user?.id]);

  useEffect(() => {
    loadQuizSets();
    loadResponses();
  }, [loadQuizSets, loadResponses]);

  // Save a response
  const saveResponse = useCallback(async (questionIda: string, answerIda: string, isCorrect: boolean) => {
    if (!user?.id) return;
    const newResponse: QuizResponse = {
      question_ida: questionIda,
      answer_ida: answerIda,
      correct: isCorrect,
      dt: new Date().toISOString(),
    };
    const updated = [...responses.filter(r => r.question_ida !== questionIda), newResponse];
    setResponses(updated);

    try {
      await saveRecord('setting', {
        model_name: 'setting',
        name: `alice-employee-qa-response-${user.id}`,
        purpose: 'alice_quiz_response',
        config: { responses: updated, user_id: user.id, user_email: user.email },
      });
    } catch (err) {
      console.error('[AliceQuiz] Failed to save response:', err);
    }
  }, [user, responses]);

  const startQuiz = (set: QuizSet) => {
    setSelectedSet(set);
    setCurrentIdx(0);
    setSelectedAnswer(null);
    setSubmitted(false);
    setMode('take');
  };

  const handleAnswer = (ida: string) => {
    if (submitted) return;
    setSelectedAnswer(ida);
  };

  const handleSubmit = () => {
    if (selectedAnswer === null || !selectedSet) return;
    const q = selectedSet.questions[currentIdx];
    const isCorrect = q.correct ? selectedAnswer === q.correct : false;
    saveResponse(q.ida, selectedAnswer, isCorrect);
    setSubmitted(true);
  };

  const handleNext = () => {
    if (!selectedSet) return;
    if (currentIdx < selectedSet.questions.length - 1) {
      setCurrentIdx(currentIdx + 1);
      setSelectedAnswer(null);
      setSubmitted(false);
    } else {
      setMode('results');
    }
  };

  const getScore = (set: QuizSet): { answered: number; correct: number; total: number } => {
    const qIdas = new Set(set.questions.map(q => q.ida));
    const relevant = responses.filter(r => qIdas.has(r.question_ida));
    return {
      answered: relevant.length,
      correct: relevant.filter(r => r.correct).length,
      total: set.questions.length,
    };
  };

  if (loading) return <div className="p-4 text-sm text-gray-500">Loading quizzes...</div>;

  // ─── Quiz List ────────────────────────────────────────
  if (mode === 'list') {
    return (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Alice Training Quizzes</h3>
        {quizSets.length === 0 ? (
          <p className="text-sm text-gray-500">
            No quizzes available. Create Setting records named <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">alice-employee-qa-topicname</code> with
            config.questions array.
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {quizSets.map((set) => {
              const score = getScore(set);
              return (
                <button
                  key={set.setting_id}
                  onClick={() => startQuiz(set)}
                  className="rounded-lg border border-gray-200 bg-white p-4 text-left shadow-sm transition hover:border-blue-300 hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
                >
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-white capitalize">{set.topic}</h4>
                  <p className="mt-1 text-xs text-gray-500">{set.questions.length} questions</p>
                  {score.answered > 0 && (
                    <div className="mt-2 flex items-center gap-2">
                      <div className="h-1.5 flex-1 rounded-full bg-gray-200 dark:bg-gray-700">
                        <div
                          className="h-1.5 rounded-full bg-green-500"
                          style={{ width: `${(score.correct / score.total) * 100}%` }}
                        />
                      </div>
                      <span className="text-[10px] font-semibold text-gray-500">
                        {score.correct}/{score.total}
                      </span>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // ─── Take Quiz ────────────────────────────────────────
  if (mode === 'take' && selectedSet) {
    const q = selectedSet.questions[currentIdx];
    const priorResponse = responses.find(r => r.question_ida === q.ida);

    return (
      <div className="max-w-2xl">
        <div className="mb-4 flex items-center justify-between">
          <button onClick={() => setMode('list')} className="text-xs text-blue-600 hover:underline">
            Back to quizzes
          </button>
          <span className="text-xs text-gray-500">
            {currentIdx + 1} of {selectedSet.questions.length} — <span className="capitalize">{selectedSet.topic}</span>
          </span>
        </div>

        {/* Progress bar */}
        <div className="mb-6 h-1 rounded-full bg-gray-200 dark:bg-gray-700">
          <div
            className="h-1 rounded-full bg-blue-500 transition-all"
            style={{ width: `${((currentIdx + 1) / selectedSet.questions.length) * 100}%` }}
          />
        </div>

        {/* Question */}
        <h3 className="mb-4 text-base font-semibold text-gray-900 dark:text-white">{q.question}</h3>

        {/* Answers */}
        <div className="space-y-2">
          {q.answers.map((ans, idx) => {
            let style = 'border-gray-200 dark:border-gray-700 hover:border-blue-300';
            if (submitted) {
              if (q.correct && ans.ida === q.correct) style = 'border-green-500 bg-green-50 dark:bg-green-900/20';
              else if (ans.ida === selectedAnswer && ans.ida !== q.correct) style = 'border-red-400 bg-red-50 dark:bg-red-900/20';
            } else if (ans.ida === selectedAnswer) {
              style = 'border-blue-500 bg-blue-50 dark:bg-blue-900/20';
            }

            return (
              <button
                key={ans.ida}
                onClick={() => handleAnswer(ans.ida)}
                className={`flex w-full items-center gap-3 rounded-lg border p-3 text-left text-sm transition ${style}`}
              >
                <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border border-gray-300 text-xs font-semibold dark:border-gray-600">
                  {String.fromCharCode(65 + idx)}
                </span>
                <span className="text-gray-800 dark:text-gray-200">{ans.answer}</span>
              </button>
            );
          })}
        </div>

        {/* Submit / Next */}
        <div className="mt-6 flex items-center gap-3">
          {!submitted ? (
            <button
              onClick={handleSubmit}
              disabled={selectedAnswer === null}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-40"
            >
              Submit Answer
            </button>
          ) : (
            <>
              {q.explanation && (
                <p className="flex-1 text-xs text-gray-600 dark:text-gray-400 italic">{q.explanation}</p>
              )}
              <button
                onClick={handleNext}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
              >
                {currentIdx < selectedSet.questions.length - 1 ? 'Next' : 'See Results'}
              </button>
            </>
          )}
        </div>

        {/* Prior answer indicator */}
        {priorResponse && !submitted && (
          <p className="mt-3 text-[10px] text-gray-400">
            Previously answered: {priorResponse.correct ? 'Correct' : 'Incorrect'} on {new Date(priorResponse.dt).toLocaleDateString()}
          </p>
        )}
      </div>
    );
  }

  // ─── Results ──────────────────────────────────────────
  if (mode === 'results' && selectedSet) {
    const score = getScore(selectedSet);
    const pct = score.total > 0 ? Math.round((score.correct / score.total) * 100) : 0;

    return (
      <div className="max-w-2xl">
        <button onClick={() => setMode('list')} className="mb-4 text-xs text-blue-600 hover:underline">
          Back to quizzes
        </button>

        <div className="rounded-xl border border-gray-200 bg-white p-6 text-center shadow-sm dark:border-gray-700 dark:bg-gray-800">
          <h3 className="text-lg font-bold text-gray-900 dark:text-white capitalize">{selectedSet.topic}</h3>
          <p className="mt-4 text-4xl font-bold text-blue-600">{pct}%</p>
          <p className="mt-1 text-sm text-gray-500">{score.correct} of {score.total} correct</p>

          <div className="mt-6 space-y-2 text-left">
            {selectedSet.questions.map((q) => {
              const r = responses.find(r => r.question_ida === q.ida);
              return (
                <div key={q.ida} className="flex items-center gap-2 text-xs">
                  <span className={`flex-shrink-0 ${r?.correct ? 'text-green-500' : r ? 'text-red-400' : 'text-gray-300'}`}>
                    {r?.correct ? '●' : r ? '○' : '—'}
                  </span>
                  <span className="text-gray-700 dark:text-gray-300 truncate">{q.question}</span>
                </div>
              );
            })}
          </div>

          <button
            onClick={() => startQuiz(selectedSet)}
            className="mt-6 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            Retake Quiz
          </button>
        </div>
      </div>
    );
  }

  return null;
}
