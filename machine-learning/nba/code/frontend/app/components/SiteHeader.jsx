export function SiteHeader() {
  return (
    <header className="masthead">
      <a href="/" className="brand">
        <span className="mark" aria-hidden="true">◉</span>
        <span>NBA Player Similarity</span>
      </a>
      <a className="github-button" href="https://github.com/mjcdata/ai-lab/tree/main/machine-learning/nba">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true" focusable="false">
          <path d="M12 .75a11.25 11.25 0 0 0-3.558 21.922c.563.103.77-.244.77-.543 0-.267-.01-.975-.015-1.914-3.13.68-3.79-1.508-3.79-1.508-.512-1.3-1.25-1.647-1.25-1.647-1.022-.699.077-.685.077-.685 1.13.08 1.725 1.16 1.725 1.16 1.005 1.722 2.637 1.225 3.28.937.102-.728.393-1.225.715-1.507-2.498-.284-5.124-1.25-5.124-5.565 0-1.23.44-2.233 1.16-3.02-.117-.285-.503-1.43.11-2.98 0 0 .945-.303 3.094 1.154a10.78 10.78 0 0 1 5.625 0c2.148-1.457 3.09-1.154 3.09-1.154.617 1.55.23 2.695.114 2.98.722.787 1.158 1.79 1.158 3.02 0 4.327-2.63 5.278-5.137 5.557.404.35.766 1.04.766 2.096 0 1.513-.014 2.734-.014 3.106 0 .302.203.652.774.541A11.252 11.252 0 0 0 12 .75Z" />
        </svg>
        View on GitHub
      </a>
    </header>
  );
}
