import { useMutation } from "@tanstack/react-query";
import { Mail, Sparkles, Target, X } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { api } from "../api";
import { BrandMark } from "../components/BrandMark";

interface HomePageProps {
  initialWaitlistOpen?: boolean;
}

export function HomePage({ initialWaitlistOpen = false }: HomePageProps) {
  const [isModalOpen, setIsModalOpen] = useState(initialWaitlistOpen);
  const [email, setEmail] = useState("");

  useEffect(() => {
    setIsModalOpen(initialWaitlistOpen);
  }, [initialWaitlistOpen]);

  const waitlistMutation = useMutation({
    mutationFn: (address: string) => api.joinWaitlist({ email: address }),
  });

  const openModal = () => {
    waitlistMutation.reset();
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEmail("");
    waitlistMutation.reset();
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void waitlistMutation.mutateAsync(email);
  };

  const successMessage = waitlistMutation.data?.already_registered
    ? "This email is already on the waitlist."
    : "You have been added to the waitlist.";

  return (
    <div className="public-shell">
      <header className="public-header">
        <div className="public-brand" aria-label="Stag">
          <BrandMark className="public-brand__mark" />
          <strong>Stag</strong>
        </div>
      </header>

      <main className="public-main">
        <section className="public-hero" aria-labelledby="public-hero-title">
          <span className="public-label">Weekly AI Newsletter</span>
          <h1 id="public-hero-title">Your personalized weekly AI briefing.</h1>
          <p className="public-description">
            Get a weekly AI newsletter tailored to your interests, so you can stay informed without
            sorting through every update yourself.
          </p>
          <button className="primary-button public-cta" type="button" onClick={openModal}>
            Join the waitlist
          </button>
          <p className="public-supporting-copy">
            Free private beta &middot; Delivered weekly &middot; Unsubscribe anytime
          </p>
        </section>

        <section className="public-section public-section-alt" aria-labelledby="public-how-title">
          <div className="public-section__inner public-section__inner-workflow">
            <div className="public-section__header">
              <span className="public-section__eyebrow">How Stag works</span>
              <h2 id="public-how-title">A simple weekly routine.</h2>
            </div>

            <div className="public-steps">
              <article className="public-step">
                <div className="public-step__top">
                  <span className="public-step__number">01</span>
                  <Target size={16} />
                </div>
                <h3>Set your interests</h3>
                <p>Tell Stag which areas of AI you want to follow most closely.</p>
              </article>

              <article className="public-step">
                <div className="public-step__top">
                  <span className="public-step__number">02</span>
                  <Sparkles size={16} />
                </div>
                <h3>Get a tailored issue</h3>
                <p>Each week, Stag prepares a newsletter shaped around the topics you care about.</p>
              </article>

              <article className="public-step">
                <div className="public-step__top">
                  <span className="public-step__number">03</span>
                  <Mail size={16} />
                </div>
                <h3>Read with clarity</h3>
                <p>Your briefing arrives concise, clear, and easy to follow.</p>
              </article>
            </div>
          </div>
        </section>

        <section className="public-section" aria-labelledby="public-signal-title">
          <div className="public-section__inner public-section__inner-signal">
            <div className="public-copy-block">
              <h2 id="public-signal-title">Less noise. More signal.</h2>
              <p>
                AI news moves quickly. Stag gives you a personalized weekly briefing, so you can
                stay current without checking every source yourself.
              </p>
            </div>

            <div className="public-benefits" aria-label="Core benefits">
              <span>Personalized to your interests</span>
              <span>Delivered weekly</span>
              <span>Clear and easy to follow</span>
            </div>
          </div>
        </section>

        <section className="public-section public-cta-section" aria-labelledby="public-cta-title">
          <div className="public-section__inner public-section__inner-cta">
            <div className="public-copy-block">
              <h2 id="public-cta-title">Stay informed without chasing every update.</h2>
              <p>Join the private beta and get a personalized AI newsletter delivered weekly.</p>
            </div>

            <button className="primary-button public-cta" type="button" onClick={openModal}>
              Join the waitlist
            </button>
            <p className="public-supporting-copy">
              Free during the private beta &middot; Unsubscribe anytime
            </p>
          </div>
        </section>
      </main>

      <footer className="public-footer">
        <div className="public-footer__brand">
          <div className="public-footer__brand-row">
            <BrandMark className="public-brand__mark public-footer__brand-mark" />
            <strong>Stag</strong>
          </div>
          <p className="public-footer__tagline">Personalized weekly AI news, made simple.</p>
        </div>

        <div className="public-footer__meta">
          <nav className="public-footer__links" aria-label="Footer">
            <a href="#">Privacy</a>
            <a href="#">Terms</a>
            <a href="#">Contact</a>
          </nav>
          <span className="public-footer__copyright">&copy; 2026 Stag</span>
        </div>
      </footer>

      {isModalOpen ? (
        <div
          className="waitlist-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="waitlist-title"
        >
          <div className="waitlist-modal__backdrop" onClick={closeModal} />
          <section className="waitlist-modal__card">
            <button
              className="waitlist-modal__close"
              type="button"
              aria-label="Close waitlist form"
              onClick={closeModal}
            >
              <X size={16} />
            </button>

            <span className="public-label">Private beta</span>
            <h2 id="waitlist-title">Join the waitlist</h2>
            <p className="waitlist-modal__description">
              Leave your email and we&apos;ll keep you posted when Stag opens beyond internal
              testing.
            </p>

            {waitlistMutation.data ? (
              <div className="waitlist-modal__success">
                <p>{successMessage}</p>
                <button className="primary-button" type="button" onClick={closeModal}>
                  Close
                </button>
              </div>
            ) : (
              <form className="waitlist-form" onSubmit={handleSubmit}>
                <label htmlFor="waitlist-email" className="waitlist-form__label">
                  Email address
                </label>
                <input
                  id="waitlist-email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  autoComplete="email"
                  required
                />
                <button
                  className="primary-button"
                  type="submit"
                  disabled={waitlistMutation.isPending}
                >
                  {waitlistMutation.isPending ? "Joining..." : "Join the waitlist"}
                </button>
              </form>
            )}

            {waitlistMutation.error ? (
              <div className="inline-alert inline-alert-danger">
                {(waitlistMutation.error as Error).message}
              </div>
            ) : null}
          </section>
        </div>
      ) : null}
    </div>
  );
}
