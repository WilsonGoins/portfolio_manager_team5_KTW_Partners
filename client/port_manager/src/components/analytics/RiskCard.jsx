import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './RiskCard.css';


const METER_MAX_BETA = 2.0;
const MAX_DUMBBELL_ROWS = 8;      // if we do more than this its just a table, not a chart

function fmtPct(value) {
  return `${value.toFixed(1)}%`;
}

// Where a beta sits along the meter, 0-100
function meterPosition(beta) {
  return Math.min(Math.max(beta / METER_MAX_BETA, 0), 1) * 100;
}

// The one-line takeaway above the chart.
function highlightSentence(highlight) {
  if (!highlight) {
    return 'Your holdings contribute risk roughly in line with their size.';
  }

  const conjunction = highlight.direction === 'above' ? 'but' : 'but only';
  return `${highlight.symbol} is ${fmtPct(highlight.weight_pct)} of your money `
    + `${conjunction} ${fmtPct(highlight.risk_share_pct)} of your market risk.`;
}

// Anything inside this of 1.0 is parity once the numbers are rounded, and saying
// "1.0x as much risk" would dress up "no difference" as a finding.
const PARITY_BAND = 0.05;

// What the bar between the two dots means, in words.
//
// Two lines: the numbers restated plainly, then what they amount to. The second
// line is a multiple rather than a difference in percentage points, because "2.2x
// the risk" is something you can picture and "13.3 pts more of your risk than of
// your money" is not -- it makes the reader do the comparison themselves, and
// "points" is jargon on top of that.
//
// The multiple is the holding's beta over the portfolio's, which is the same
// number as its share of the risk over its share of the money. Taking it from the
// betas says why the gap exists and ties the sentence to the beta in the row.
function gapLabel(row, portfolioBeta) {
  const shares = `${fmtPct(row.weight_pct)} of your money, `
    + `${fmtPct(row.risk_share_pct)} of your market risk`;

  if (row.h_type === 'Cash') {
    return `${shares}\nCash doesn't follow the market, so it adds no market risk.`;
  }

  if (!portfolioBeta) return shares;

  const ratio = row.beta / portfolioBeta;

  if (Math.abs(ratio - 1) < PARITY_BAND) {
    return `${shares}\nIts beta of ${row.beta.toFixed(2)} is about average for your `
      + 'portfolio, so it carries risk in step with its size.';
  }

  if (ratio > 1) {
    return `${shares}\nIts beta of ${row.beta.toFixed(2)} is above your portfolio's `
      + `${portfolioBeta.toFixed(2)}, so each dollar here carries ${ratio.toFixed(1)}x `
      + 'the market risk of an average dollar in your portfolio.';
  }

  return `${shares}\nIts beta of ${row.beta.toFixed(2)} is below your portfolio's `
    + `${portfolioBeta.toFixed(2)}, so each dollar here carries ${(1 / ratio).toFixed(1)}x `
    + 'less market risk than an average dollar in your portfolio.';
}

// One holding's two dots. The left dot is its share of the money, the right its
// share of the risk, and the connector between them is the whole point -- a long
// bar means the holding carries a lot more (or a lot less) risk than its size
// suggests
function DumbbellRow({ row, scaleMax, muted, onSelect, portfolioBeta }) {
  const moneyPos = (row.weight_pct / scaleMax) * 100;
  const riskPos = (row.risk_share_pct / scaleMax) * 100;

  const left = Math.min(moneyPos, riskPos);
  const width = Math.abs(riskPos - moneyPos);

  const body = (
    <>
      {/* cash carries "--" as its symbol the way it does everywhere else, so the
          row is labelled by name instead */}
      <span className="dumbbell-symbol" title={row.name}>
        {row.symbol === '--' ? row.name : row.symbol}
      </span>

      {/* the gap sits on the track rather than on the connector alone: when a
          holding's two shares match, the connector has no width to hover */}
      <span className="dumbbell-track" title={gapLabel(row, portfolioBeta)}>
        <span
          className="dumbbell-connector"
          style={{ left: `${left}%`, width: `${width}%` }}
        />
        <span
          className="dumbbell-dot dumbbell-dot-money"
          style={{ left: `${moneyPos}%` }}
          title={`${fmtPct(row.weight_pct)} of your money`}
        />
        <span
          className="dumbbell-dot dumbbell-dot-risk"
          style={{ left: `${riskPos}%` }}
          title={`${fmtPct(row.risk_share_pct)} of your market risk`}
        />
      </span>

      <span className="dumbbell-values">
        <span className="dumbbell-value">{fmtPct(row.weight_pct)}</span>
        <span className="dumbbell-arrow">→</span>
        <span className="dumbbell-value dumbbell-value-risk">{fmtPct(row.risk_share_pct)}</span>
      </span>

      <span className="dumbbell-beta">
        {row.beta === null ? '--' : row.beta.toFixed(2)}
      </span>
    </>
  );

  return (
    <li className={`dumbbell-row${muted ? ' dumbbell-row-muted' : ''}`}>
      {onSelect ? (
        // a real button, so the rows are reachable by keyboard the way the
        // holdings table's rows are by mouse
        <button type="button" className="dumbbell-row-button" onClick={onSelect}>
          {body}
        </button>
      ) : (
        <span className="dumbbell-row-static">{body}</span>
      )}
    </li>
  );
}

export function RiskCard({ data }) {
  const [showInfo, setShowInfo] = useState(false);
  const navigate = useNavigate();

  // same destination the Overview's holdings table sends a clicked row to, and
  // the same guard: cash carries "--" and has no security page to open
  const openDetails = (symbol) => {
    if (symbol && symbol !== '--') navigate(`/details/${symbol}`);
  };

  const {
    portfolio_beta: portfolioBeta,
    risk_level: riskLevel,
    coverage_pct: coveragePct,
    holdings,
    beta_bands: bands,
    highlight,
  } = data;

  // A holding with no beta isn't published by Yahoo. We name
  // it in the footnote instead and keep it out of the plot 
  const rated = holdings.filter((row) => row.beta !== null);
  const unrated = holdings.filter((row) => row.beta === null);

  // Cash has no beta, so just keep it at the bottom in a muted color
  const cash = rated.find((row) => row.h_type === 'Cash');
  const allPositions = rated.filter((row) => row.h_type !== 'Cash');
  const positions = allPositions.slice(0, MAX_DUMBBELL_ROWS);
  const hiddenCount = allPositions.length - positions.length;

  const plotted = cash ? [...positions, cash] : positions;

  // Both dots share one scale, otherwise the gap between them would be a drawing
  // artefact rather than the actual difference the row exists to show.
  const scaleMax = Math.max(
    ...plotted.flatMap((row) => [row.weight_pct, row.risk_share_pct]),
    1,
  ) * 1.08;

  const conservativeEnd = meterPosition(bands.conservative_ceiling);
  const marketEnd = meterPosition(bands.market_ceiling);

  return (
    <div className="card risk-card">
      <div className="risk-card-header">
        <h3>Portfolio Risk</h3>
        <button
          type="button"
          className="risk-info-toggle"
          onClick={() => setShowInfo((open) => !open)}
          aria-expanded={showInfo}
          title="What is beta?"
        >
          ⓘ
        </button>
      </div>

      {showInfo && (
        <p className="risk-info-body">
          <strong>Beta</strong> measures how much your holdings move when the
          market moves. 1.0 means they move with the market, 2.0 means they move
          twice as much, and 0 means they don&apos;t follow it at all.
        </p>
      )}

      <div className="risk-headline">
        <span className="risk-beta">{portfolioBeta.toFixed(2)}</span>
        <span className="risk-beta-label">beta</span>
        <span className={`risk-level-chip risk-level-${riskLevel.toLowerCase()}`}>
          {riskLevel}
        </span>
      </div>

      <div className="risk-meter">
        <div className="risk-meter-track">
          {/* the band the "Market" label is decided by, shaded so the chip above
              and the marker below are visibly talking about the same range */}
          <div
            className="risk-meter-band"
            style={{ left: `${conservativeEnd}%`, width: `${marketEnd - conservativeEnd}%` }}
          />
          <div
            className="risk-meter-marker"
            style={{ left: `${meterPosition(portfolioBeta)}%` }}
          />
        </div>
        <div className="risk-meter-scale">
          <span>0</span>
          <span>defensive</span>
          <span>with market</span>
          <span>amplified</span>
          <span>{METER_MAX_BETA.toFixed(1)}+</span>
        </div>
      </div>

      {/* the prefix marks this as an illustration of what the chart below shows,
          rather than a separate finding the page is reporting */}
      <p className="risk-takeaway">
        <span className="risk-takeaway-prefix">ex)</span>
        {highlightSentence(highlight)}
      </p>

      <div className="risk-dumbbell">
        <div className="dumbbell-legend">
          <span className="dumbbell-legend-item">
            <span className="dumbbell-dot dumbbell-dot-money dumbbell-dot-static" />
            your money
          </span>
          <span className="dumbbell-legend-item">
            <span className="dumbbell-dot dumbbell-dot-risk dumbbell-dot-static" />
            your market risk
          </span>
          <span className="dumbbell-legend-beta">beta</span>
        </div>

        <ul className="dumbbell-rows">
          {plotted.map((row) => (
            <DumbbellRow
              key={row.symbol === '--' ? 'cash' : row.symbol}
              row={row}
              scaleMax={scaleMax}
              muted={row.h_type === 'Cash'}
              portfolioBeta={portfolioBeta}
              onSelect={row.symbol === '--' ? null : () => openDetails(row.symbol)}
            />
          ))}
        </ul>
      </div>

      <p className="risk-footnote">
        Based on {coveragePct.toFixed(0)}% of your portfolio
        {unrated.length > 0 && (
          <> · {unrated.map((row) => row.symbol).join(', ')} not rated by Yahoo</>
        )}
        {hiddenCount > 0 && (
          <> · {hiddenCount} smaller {hiddenCount === 1 ? 'holding' : 'holdings'} not shown</>
        )}
      </p>
    </div>
  );
}
