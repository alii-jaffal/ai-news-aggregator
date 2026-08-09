import { useMutation } from "@tanstack/react-query";
import { FormEvent, MouseEvent, useEffect, useRef, useState } from "react";

import { api } from "../api";
import stagLogoUrl from "../assets/Stag-logo.png";
import "./homepage.css";

interface HomePageProps {
  initialWaitlistOpen?: boolean;
}

const topics = ["AI models", "Agents", "Research", "Developer tools"];
const WAITLIST_FOCUS_DELAY_MS = 260;
const WAITLIST_BELOW_CENTER_OFFSET = 56;

function ArrowIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 16 16" fill="none">
      <path d="M3 8h10M9.5 4.5 13 8l-3.5 3.5" />
    </svg>
  );
}

function LogoMark() {
  return (
    <span className="stag-homepage__logo-mark" aria-hidden="true">
      <img className="stag-homepage__logo-mark-image" src={stagLogoUrl} alt="" />
    </span>
  );
}

export function HomePage({ initialWaitlistOpen = false }: HomePageProps) {
  const [email, setEmail] = useState("");
  const emailInputRef = useRef<HTMLInputElement>(null);
  const waitlistRef = useRef<HTMLDivElement>(null);

  const waitlistMutation = useMutation({
    mutationFn: (address: string) => api.joinWaitlist({ email: address }),
  });

  const focusWaitlist = () => {
    const scrollTarget = emailInputRef.current ?? waitlistRef.current;

    if (!scrollTarget) {
      return;
    }

    const { top, height } = scrollTarget.getBoundingClientRect();
    const targetTop =
      top + window.scrollY - window.innerHeight / 2 + height / 2 - WAITLIST_BELOW_CENTER_OFFSET;

    window.scrollTo({
      top: Math.max(targetTop, 0),
      behavior: "smooth",
    });

    window.setTimeout(() => {
      emailInputRef.current?.focus({ preventScroll: true });
    }, WAITLIST_FOCUS_DELAY_MS);
  };

  const handleWaitlistJump = (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    focusWaitlist();
  };

  useEffect(() => {
    if (!initialWaitlistOpen) {
      return;
    }

    focusWaitlist();
  }, [initialWaitlistOpen]);

  const submitWaitlist = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void waitlistMutation.mutateAsync(email);
  };

  const successMessage = waitlistMutation.data?.already_registered
    ? "You're already on the waitlist."
    : "You're on the waitlist.";

  return (
    <div className="stag-homepage-page">
      <main className="stag-homepage">
        <header className="stag-homepage__header">
          <a className="stag-homepage__brand" href="#top" aria-label="Stag home">
            <LogoMark />
            <span>Stag</span>
          </a>
          <a className="stag-homepage__header-link" href="#waitlist" onClick={handleWaitlistJump}>
            Join waitlist
          </a>
        </header>

        <section className="stag-homepage__hero" id="top">
          <p className="stag-homepage__eyebrow">Personalized AI news, once a week</p>
          <h1>
            Keep up with AI.
            <br />
            Skip the noise.
          </h1>
          <p className="stag-homepage__intro">
            A short weekly briefing shaped around your interests and experience. Read what matters,
            then get back to your work.
          </p>

          <div className="stag-homepage__waitlist" id="waitlist" ref={waitlistRef}>
            {waitlistMutation.data ? (
              <div className="stag-homepage__success" role="status">
                <span aria-hidden="true">&check;</span>
                {successMessage}
              </div>
            ) : (
              <form className="stag-homepage__form" onSubmit={submitWaitlist}>
                <label className="stag-homepage__sr-only" htmlFor="email">
                  Email address
                </label>
                <input
                  id="email"
                  ref={emailInputRef}
                  name="email"
                  type="email"
                  placeholder="Email address"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
                <button type="submit" disabled={waitlistMutation.isPending}>
                  {waitlistMutation.isPending ? "Joining..." : "Join waitlist"}
                  <ArrowIcon />
                </button>
              </form>
            )}

            {waitlistMutation.error ? (
              <p className="stag-homepage__error" role="alert">
                {(waitlistMutation.error as Error).message}
              </p>
            ) : null}

            <p className="stag-homepage__waitlist-note">Free during private beta. No daily emails.</p>
          </div>
        </section>

        <section className="stag-homepage__how-it-works" aria-labelledby="how-it-works-title">
          <div className="stag-homepage__section-heading">
            <div>
              <p className="stag-homepage__section-label">How Stag works</p>
              <h2 id="how-it-works-title">A simple weekly routine.</h2>
            </div>
            <a className="stag-homepage__section-link" href="#waitlist" onClick={handleWaitlistJump}>
              Join waitlist
              <ArrowIcon />
            </a>
          </div>

          <div className="stag-homepage__steps">
            <article>
              <span>01</span>
              <h3>Choose your interests</h3>
              <p>
                Select the AI topics you care about and how technical you want your briefing to be.
              </p>
            </article>
            <article>
              <span>02</span>
              <h3>Get a tailored issue</h3>
              <p>Each week, Stag prepares a concise issue shaped around what is relevant to you.</p>
            </article>
            <article>
              <span>03</span>
              <h3>Read it in five minutes</h3>
              <p>Your Sunday briefing arrives clear, focused, and easy to finish in one sitting.</p>
            </article>
          </div>
        </section>

        <section className="stag-homepage__product-preview" aria-label="Example weekly briefing">
          <div className="stag-homepage__preview-topline">
            <span>YOUR WEEK IN AI</span>
            <span>ISSUE 024 &middot; 5 MIN</span>
          </div>

          <div className="stag-homepage__preview-heading">
            <div>
              <p>Curated for Ali</p>
              <h2>Good morning.</h2>
            </div>
            <div className="stag-homepage__topic-list" aria-label="Selected interests">
              {topics.map((topic) => (
                <span key={topic}>{topic}</span>
              ))}
            </div>
          </div>

          <ol className="stag-homepage__story-list">
            <li>
              <span>01</span>
              <div>
                <small>THE BIG STORY</small>
                <strong>Smaller AI models are becoming useful in production</strong>
              </div>
              <span aria-hidden="true">&rarr;</span>
            </li>
            <li>
              <span>02</span>
              <div>
                <small>WORTH KNOWING</small>
                <strong>Agent tools move from demos to repeatable workflows</strong>
              </div>
              <span aria-hidden="true">&rarr;</span>
            </li>
            <li>
              <span>03</span>
              <div>
                <small>ON YOUR RADAR</small>
                <strong>Open-source inference gets cheaper and simpler</strong>
              </div>
              <span aria-hidden="true">&rarr;</span>
            </li>
          </ol>
        </section>

        <section className="stag-homepage__closing-cta" aria-labelledby="closing-cta-title">
          <div>
            <p className="stag-homepage__section-label">One useful email. Once a week.</p>
            <h2 id="closing-cta-title">Your week in AI, without the noise.</h2>
          </div>
          <a className="stag-homepage__closing-link" href="#waitlist" onClick={handleWaitlistJump}>
            Join waitlist
            <ArrowIcon />
          </a>
        </section>

        <footer className="stag-homepage__footer">
          <a className="stag-homepage__brand" href="#top" aria-label="Stag home">
            <LogoMark />
            <span>Stag</span>
          </a>
          <p>AI news, made personal.</p>
          <span>&copy; 2026</span>
        </footer>
      </main>
    </div>
  );
}
