"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { prettySkill } from "@/lib/status";
import type { GapItem, Role } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { EmptyState, LoadingState } from "@/components/ui/States";

type Props = {
  roles: Role[];
  selected: string;
  onSelect: (slug: string) => void;
  query: string;
  onQueryChange: (value: string) => void;
  learnerId?: string | null;
  onLoadError?: (message: string | null) => void;
};

type RolePreview = {
  coreSkills: string[];
  competencyCount: number;
  topGaps: GapItem[];
};

export function CareerExplorer({
  roles,
  selected,
  onSelect,
  query,
  onQueryChange,
  learnerId,
  onLoadError,
}: Props) {
  const [preview, setPreview] = useState<RolePreview>({ coreSkills: [], competencyCount: 0, topGaps: [] });
  const [compareSlug, setCompareSlug] = useState("");
  const [comparePreview, setComparePreview] = useState<RolePreview | null>(null);
  const [compareOpen, setCompareOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [compareLoading, setCompareLoading] = useState(false);
  const [peek, setPeek] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return roles;
    return roles.filter(
      (role) =>
        role.name.toLowerCase().includes(needle) ||
        role.description.toLowerCase().includes(needle) ||
        role.slug.includes(needle),
    );
  }, [query, roles]);

  async function loadPreview(slug: string): Promise<RolePreview> {
    const profile = await api.roleCompetencies(slug);
    const coreSkills = profile.competencies
      .filter((item) => item.required_status === "CORE")
      .slice(0, 8)
      .map((item) => item.skill);
    let topGaps: GapItem[] = [];
    if (learnerId) {
      const gaps = await api.gaps(learnerId, slug);
      topGaps = gaps.items.filter((item) => item.gap_status !== "MET").slice(0, 5);
    }
    return { coreSkills, competencyCount: profile.competencies.length, topGaps };
  }

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    onLoadError?.(null);
    loadPreview(selected)
      .then(setPreview)
      .catch((err: Error) => {
        setPreview({ coreSkills: [], competencyCount: 0, topGaps: [] });
        onLoadError?.(err.message);
      })
      .finally(() => setLoading(false));
  }, [selected, learnerId, onLoadError]);

  useEffect(() => {
    if (!compareOpen || !compareSlug || compareSlug === selected) {
      setComparePreview(null);
      return;
    }
    setCompareLoading(true);
    loadPreview(compareSlug)
      .then(setComparePreview)
      .catch(() => setComparePreview(null))
      .finally(() => setCompareLoading(false));
  }, [compareOpen, compareSlug, selected, learnerId]);

  const selectedRole = roles.find((role) => role.slug === selected);
  const compareRole = roles.find((role) => role.slug === compareSlug);

  return (
    <div className="career-explorer space-y-4">
      <div className="career-explorer-head">
        <p className="type-section">{roles.length} careers to explore</p>
        <p className="mt-1 text-sm text-mist">Each role produces a different gap profile and sequenced path.</p>
      </div>
      <label className="sr-only" htmlFor="career-search">
        Search careers
      </label>
      <input
        id="career-search"
        className="career-search field-inline w-full text-paper"
        placeholder="Search careers…"
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
      />
      <div className="career-grid grid gap-2 sm:grid-cols-2">
        {filtered.map((role) => {
          const isSelected = selected === role.slug;
          const isPeek = peek === role.slug && !isSelected;
          return (
            <button
              key={role.slug}
              type="button"
              onClick={() => onSelect(role.slug)}
              onMouseEnter={() => setPeek(role.slug)}
              onMouseLeave={() => setPeek((current) => (current === role.slug ? null : current))}
              onFocus={() => setPeek(role.slug)}
              onBlur={() => setPeek((current) => (current === role.slug ? null : current))}
              aria-pressed={isSelected}
              className={`career-card text-left ${isSelected ? "career-card-active" : ""} ${isPeek ? "is-peek" : ""}`}
            >
              <div className="career-card-route" aria-hidden>
                <span className={`career-route-node ${isSelected ? "is-live" : ""}`} />
                <span className={`career-route-line ${isSelected ? "is-live" : ""}`} />
                <span className={`career-route-dest ${isSelected ? "is-live" : ""}`} />
              </div>
              <p className="career-card-name">{role.name}</p>
              <p className="career-card-identity mt-1 line-clamp-2">{role.description}</p>
              <p className="career-card-teaser mt-2 font-mono text-[10px] uppercase tracking-wider text-mist">
                {isSelected ? "Selected · preview below" : "Select to preview fit"}
              </p>
            </button>
          );
        })}
        {!filtered.length ? (
          <div className="col-span-full">
            <EmptyState title="No careers match" body="Try a different search term." />
          </div>
        ) : null}
      </div>

      {loading ? (
        <div className="onboard-inline-status">
          <LoadingState label="Loading role requirements" />
        </div>
      ) : null}

      {!loading && selectedRole ? (
        <div className="career-requirements">
          <p className="type-section">Route preview · {selectedRole.name}</p>
          <p className="mt-2 text-sm text-mist">{selectedRole.description}</p>
          <p className="mt-2 text-sm text-mist">{preview.competencyCount} competencies tracked</p>
          {preview.coreSkills.length ? (
            <>
              <p className="mt-3 text-xs uppercase tracking-[0.18em] text-mist">Core competencies</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {preview.coreSkills.map((skill) => (
                  <span key={skill} className="career-skill-chip">
                    {prettySkill(skill)}
                  </span>
                ))}
              </div>
            </>
          ) : null}
          {learnerId && preview.topGaps.length ? (
            <>
              <p className="mt-4 text-xs uppercase tracking-[0.18em] text-mist">Current learner fit · top gaps</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {preview.topGaps.map((gap) => (
                  <span key={gap.skill} className="career-gap-chip">
                    {prettySkill(gap.skill)}
                  </span>
                ))}
              </div>
            </>
          ) : null}
          <p className="career-choose mt-4 text-sm text-paper">Choose this destination to sequence the path.</p>
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <Button variant="ghost" onClick={() => setCompareOpen((open) => !open)}>
          {compareOpen ? "Hide comparison" : "Compare two careers"}
        </Button>
      </div>

      {compareOpen ? (
        <div className="career-compare grid gap-4 md:grid-cols-2" data-testid="career-compare">
          <label className="text-xs uppercase tracking-[0.16em] text-mist">
            Role A
            <select
              className="field-inline mt-2 w-full text-paper"
              value={selected}
              onChange={(event) => onSelect(event.target.value)}
            >
              {roles.map((role) => (
                <option key={role.slug} value={role.slug}>
                  {role.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs uppercase tracking-[0.16em] text-mist">
            Role B
            <select
              className="field-inline mt-2 w-full text-paper"
              value={compareSlug}
              onChange={(event) => setCompareSlug(event.target.value)}
            >
              <option value="">Choose a role…</option>
              {roles
                .filter((role) => role.slug !== selected)
                .map((role) => (
                  <option key={role.slug} value={role.slug}>
                    {role.name}
                  </option>
                ))}
            </select>
          </label>
          {compareLoading ? <LoadingState label="Loading comparison" /> : null}
          {!compareLoading && comparePreview && compareRole ? (
            <>
              <CompareColumn title={selectedRole?.name ?? "Role A"} preview={preview} learnerFit={Boolean(learnerId)} />
              <CompareColumn title={compareRole.name} preview={comparePreview} learnerFit={Boolean(learnerId)} />
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function CompareColumn({
  title,
  preview,
  learnerFit,
}: {
  title: string;
  preview: RolePreview;
  learnerFit: boolean;
}) {
  return (
    <div className="career-compare-col">
      <p className="compare-title">{title}</p>
      <p className="mt-5 type-section">Core skills</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {preview.coreSkills.map((skill) => (
          <span key={skill} className="career-skill-chip">
            {prettySkill(skill)}
          </span>
        ))}
      </div>
      <p className="mt-5 type-section">Current fit</p>
      <p className="mt-2 font-mono text-xs tabular-nums text-mist">
        {preview.competencyCount} competencies tracked
      </p>
      {learnerFit ? (
        <>
          <p className="mt-5 type-section">Top gaps</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {preview.topGaps.length ? (
              preview.topGaps.map((gap) => (
                <span key={gap.skill} className="career-gap-chip">
                  {prettySkill(gap.skill)}
                </span>
              ))
            ) : (
              <span className="text-xs text-mist">No open gaps yet</span>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
