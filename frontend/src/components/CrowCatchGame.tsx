import { useEffect, useRef, useState } from "react";

const INITIAL_TIME_MS = 1500;
const TIME_STEP_MS = 50;
const MIN_TIME_MS = 500;
const MAX_ERRORS = 3;
const CROW_SIZE_PX = 44;

type GameMode = "invite" | "instructions" | "playing" | "finished";

interface Props {
  analysisActive: boolean;
  operation: "topics" | "feedback";
}

interface Position {
  left: number;
  top: number;
}

function durationFor(score: number) {
  return Math.max(MIN_TIME_MS, INITIAL_TIME_MS - score * TIME_STEP_MS);
}

export default function CrowCatchGame({ analysisActive, operation }: Props) {
  const [mode, setMode] = useState<GameMode>("invite");
  const [score, setScore] = useState(0);
  const [errors, setErrors] = useState(0);
  const [position, setPosition] = useState<Position | null>(null);
  const [instructionAction, setInstructionAction] = useState<"new" | "resume">("new");
  const arenaRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<number | null>(null);
  const modeRef = useRef<GameMode>("invite");
  const roundRef = useRef(0);
  const scoreRef = useRef(0);
  const errorsRef = useRef(0);

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  function clearTimer() {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }

  function spawn() {
    clearTimer();
    const arena = arenaRef.current;
    if (
      !arena ||
      document.visibilityState === "hidden" ||
      !analysisActive ||
      modeRef.current !== "playing"
    ) return;
    const width = Math.max(0, arena.clientWidth - CROW_SIZE_PX);
    const height = Math.max(0, arena.clientHeight - CROW_SIZE_PX);
    const round = roundRef.current + 1;
    roundRef.current = round;
    setPosition({
      left: Math.floor(Math.random() * (width + 1)),
      top: Math.floor(Math.random() * (height + 1)),
    });
    timerRef.current = window.setTimeout(() => {
      if (
        roundRef.current !== round ||
        document.visibilityState === "hidden" ||
        modeRef.current !== "playing"
      ) return;
      setPosition(null);
      spawn();
    }, durationFor(scoreRef.current));
  }

  function showInstructions() {
    clearTimer();
    roundRef.current += 1;
    setPosition(null);
    setInstructionAction("resume");
    setMode("instructions");
  }

  function begin() {
    setScore(0);
    setErrors(0);
    scoreRef.current = 0;
    errorsRef.current = 0;
    setPosition(null);
    setMode("playing");
  }

  function resume() {
    setMode("playing");
  }

  function hide() {
    clearTimer();
    roundRef.current += 1;
    setPosition(null);
    setMode("invite");
  }

  function miss() {
    if (modeRef.current !== "playing" || position === null) return;
    const nextErrors = errorsRef.current + 1;
    errorsRef.current = nextErrors;
    setErrors(nextErrors);
    setPosition(null);
    roundRef.current += 1;
    clearTimer();
    if (nextErrors >= MAX_ERRORS) setMode("finished");
    else spawn();
  }

  function catchCrow() {
    if (modeRef.current !== "playing" || position === null) return;
    roundRef.current += 1;
    clearTimer();
    const nextScore = scoreRef.current + 1;
    scoreRef.current = nextScore;
    setScore(nextScore);
    setPosition(null);
    spawn();
  }

  useEffect(() => {
    if (!analysisActive) {
      clearTimer();
      roundRef.current += 1;
      setPosition(null);
      setMode("invite");
    }
  }, [analysisActive]);

  useEffect(() => {
    if (mode !== "playing" || !analysisActive) return;
    const frame = window.requestAnimationFrame(spawn);
    return () => {
      window.cancelAnimationFrame(frame);
      clearTimer();
    };
  }, [mode, analysisActive]);

  useEffect(() => {
    function onVisibilityChange() {
      if (document.visibilityState === "hidden") {
        clearTimer();
        roundRef.current += 1;
        setPosition(null);
      } else if (modeRef.current === "playing" && analysisActive) {
        spawn();
      }
    }
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", onVisibilityChange);
      clearTimer();
    };
  }, [analysisActive]);

  if (!analysisActive) return null;
  const waitingText = operation === "topics"
    ? "enquanto identificamos os tópicos do material."
    : "enquanto preparamos seu feedback.";

  return (
    <section className="crow-game" aria-label="Passatempo opcional">
      {mode === "invite" && (
        <div className="crow-game-invite">
          <img src="/corvo.svg" alt="" aria-hidden="true" />
          <div>
            <h2>Que tal jogar enquanto espera?</h2>
            <p>Pegue os corvos e tente bater sua pontuação {waitingText}</p>
          </div>
          <button className="btn secondary-btn" type="button" onClick={() => { setInstructionAction("new"); setMode("instructions"); }}>
            Jogar
          </button>
        </div>
      )}

      {mode !== "invite" && (
        <>
          <div className="crow-game-heading">
            <div>
              <h2>Pegue o corvo</h2>
              {mode === "playing" && <p>Acerte o corvo. Você pode errar até 3 vezes.</p>}
            </div>
            <button className="text-button" type="button" onClick={hide}>Ocultar jogo</button>
          </div>

          {mode === "instructions" && (
            <div className="crow-game-instructions">
              <p>Clique no corvo antes que ele desapareça.</p>
              <ul>
                <li>Cada acerto vale 1 ponto.</li>
                <li>Quanto mais pontos, menos tempo o corvo fica na tela.</li>
                <li>Clicar no espaço vazio da arena conta como erro.</li>
                <li>Com 3 erros, a rodada termina.</li>
                <li>Se o corvo desaparecer sem um clique, você não perde uma chance.</li>
              </ul>
              <p>Este minijogo é jogado com o mouse.</p>
              <button className="btn" type="button" onClick={instructionAction === "resume" ? resume : begin}>
                {instructionAction === "resume" ? "Continuar" : "Começar"}
              </button>
            </div>
          )}

          {(mode === "playing" || mode === "finished") && (
            <>
              <div className="crow-game-score" aria-live="polite">
                <span>Pontuação: {score}</span>
                <span>Erros: {errors}/{MAX_ERRORS}</span>
                {mode === "playing" && <button className="text-button" type="button" onClick={showInstructions}>Como jogar</button>}
              </div>
              <div
                ref={arenaRef}
                className="crow-game-arena"
                onPointerDown={(event) => {
                  if (event.pointerType !== "mouse" || event.button !== 0) return;
                  const arena = arenaRef.current;
                  if (!arena || position === null) return;
                  const bounds = arena.getBoundingClientRect();
                  const x = event.clientX - bounds.left;
                  const y = event.clientY - bounds.top;
                  const acertou =
                    x >= position.left &&
                    x <= position.left + CROW_SIZE_PX &&
                    y >= position.top &&
                    y <= position.top + CROW_SIZE_PX;
                  if (acertou) catchCrow();
                  else miss();
                }}
                aria-label="Arena do jogo"
              >
                {position && mode === "playing" && (
                  <div
                    className="crow-game-target"
                    style={{ left: position.left, top: position.top }}
                  >
                    <img src="/corvo.svg" alt="" draggable="false" />
                  </div>
                )}
                {mode === "finished" && (
                  <div className="crow-game-finished">
                    <strong>Fim de jogo</strong>
                    <span>Sua pontuação: {score}</span>
                  </div>
                )}
              </div>
              {mode === "finished" && <button className="btn secondary-btn" type="button" onClick={() => { setInstructionAction("new"); setMode("instructions"); }}>Jogar novamente</button>}
            </>
          )}
        </>
      )}
    </section>
  );
}
