"use client";

import { FormEvent, useState } from "react";

const topics = ["AI models", "Agents", "Research", "Developer tools"];

function ArrowIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 16 16" fill="none">
      <path d="M3 8h10M9.5 4.5 13 8l-3.5 3.5" />
    </svg>
  );
}

function LogoMark() {
  return (
    <span className="logo-mark" aria-hidden="true">
      <span />
      <span />
    </span>
  );
}

export default function Home() {
  const [submitted, setSubmitted] = useState(false);

  function submitWaitlist(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
  }

  return (
    <main>
      <header>
        <a className="brand" href="#top" aria-label="Stag home">
          <LogoMark />
          <span>Stag</span>
        </a>
        <a className="header-link" href="#waitlist">
          Join waitlist
        </a>
      </header>

      <section className="hero" id="top">
        <p className="eyebrow">Personalized AI news, once a week</p>
        <h1>Keep up with AI.<br />Skip the noise.</h1>
        <p className="intro">
          A short weekly briefing shaped around your interests and experience.
          Read what matters, then get back to your work.
        </p>

        <div className="waitlist" id="waitlist">
          {submitted ? (
            <div className="success" role="status">
              <span aria-hidden="true">✓</span>
              You’re on the waitlist.
            </div>
          ) : (
            <form onSubmit={submitWaitlist}>
              <label className="sr-only" htmlFor="email">Email address</label>
              <input
                id="email"
                name="email"
                type="email"
                placeholder="Email address"
                autoComplete="email"
                required
              />
              <button type="submit">
                Join waitlist
                <ArrowIcon />
              </button>
            </form>
          )}
          <p>Free during private beta. No daily emails.</p>
        </div>
      </section>

      <section className="how-it-works" aria-labelledby="how-it-works-title">
        <div className="section-heading">
          <div>
            <p className="section-label">How Stag works</p>
            <h2 id="how-it-works-title">A simple weekly routine.</h2>
          </div>
          <a className="section-link" href="#waitlist">
            Join waitlist
            <ArrowIcon />
          </a>
        </div>

        <div className="steps">
          <article>
            <span>01</span>
            <h3>Choose your interests</h3>
            <p>Select the AI topics you care about and how technical you want your briefing to be.</p>
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

      <section className="product-preview" aria-label="Example weekly briefing">
        <div className="preview-topline">
          <span>YOUR WEEK IN AI</span>
          <span>ISSUE 024 · 5 MIN</span>
        </div>

        <div className="preview-heading">
          <div>
            <p>Curated for Ali</p>
            <h2>Good morning.</h2>
          </div>
          <div className="topic-list" aria-label="Selected interests">
            {topics.map((topic) => <span key={topic}>{topic}</span>)}
          </div>
        </div>

        <ol className="story-list">
          <li>
            <span>01</span>
            <div>
              <small>THE BIG STORY</small>
              <strong>Smaller AI models are becoming useful in production</strong>
            </div>
            <span aria-hidden="true">↗</span>
          </li>
          <li>
            <span>02</span>
            <div>
              <small>WORTH KNOWING</small>
              <strong>Agent tools move from demos to repeatable workflows</strong>
            </div>
            <span aria-hidden="true">↗</span>
          </li>
          <li>
            <span>03</span>
            <div>
              <small>ON YOUR RADAR</small>
              <strong>Open-source inference gets cheaper and simpler</strong>
            </div>
            <span aria-hidden="true">↗</span>
          </li>
        </ol>
      </section>

      <section className="closing-cta" aria-labelledby="closing-cta-title">
        <div>
          <p className="section-label">One useful email. Once a week.</p>
          <h2 id="closing-cta-title">Your week in AI, without the noise.</h2>
        </div>
        <a className="closing-link" href="#waitlist">
          Join waitlist
          <ArrowIcon />
        </a>
      </section>

      <footer>
        <a className="brand" href="#top" aria-label="Stag home">
          <LogoMark />
          <span>Stag</span>
        </a>
        <p>AI news, made personal.</p>
        <span>© 2026</span>
      </footer>
    </main>
  );
}
