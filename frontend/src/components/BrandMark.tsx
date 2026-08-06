import stagLogoUrl from "../assets/Stag-logo.png";

interface BrandMarkProps {
  className: string;
}

export function BrandMark({ className }: BrandMarkProps) {
  return (
    <div className={className} aria-hidden="true">
      <img className="brand-mark__image" src={stagLogoUrl} alt="" />
    </div>
  );
}
