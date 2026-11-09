import React from "react";
import { formatScore, getScoreColorClass } from "../lib/utils";
import type { CategoryScoreDTO, RuleCategory } from "../lib/api/client";
import {
  Globe,
  FileCode2,
  Heading,
  Image,
  Code2,
  CheckCircle,
  AlertCircle,
  HelpCircle,
} from "lucide-react";

interface CategoryScoresProps {
  categoryScores?: Record<string, CategoryScoreDTO>;
  categoryAvailability?: Record<string, boolean>;
}


interface CategoryMeta {
  title: string;
  description: string;
  icon: React.ReactNode;
}

const CATEGORY_META: Record<string, CategoryMeta> = {
  CRAWLABILITY: {
    title: "Crawlability & Network",
    description: "HTTP transport, redirect chain (E11), HTTPS enforcement, and robots directives.",
    icon: <Globe className="w-5 h-5 text-cyan-400" />,
  },
  INDEXABILITY: {
    title: "Indexability & Meta",
    description: "Title length/presence, meta description, and canonical link integrity.",
    icon: <FileCode2 className="w-5 h-5 text-blue-400" />,
  },
  DOCUMENT: {
    title: "Document Structure",
    description: "H1 count and presence, and proper hierarchical heading levels.",
    icon: <Heading className="w-5 h-5 text-indigo-400" />,
  },
  CONTENT: {
    title: "Assets & Content",
    description: "Image alt text coverage (E10) and layout stability dimensions (CLS).",
    icon: <Image className="w-5 h-5 text-teal-400" />,
  },
  STRUCTURED: {
    title: "Structured Data",
    description: "Schema.org JSON-LD syntax validation (E14) and recognized schema types.",
    icon: <Code2 className="w-5 h-5 text-violet-400" />,
  },
};

export function CategoryScores({
  categoryScores,
  categoryAvailability,
}: CategoryScoresProps) {
  const categories: RuleCategory[] = [
    "CRAWLABILITY",
    "INDEXABILITY",
    "DOCUMENT",
    "CONTENT",
    "STRUCTURED",
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold tracking-tight text-white">
          Category Health Breakdown (Model E2)
        </h3>
        <span className="text-xs text-slate-400">
          5 Core Architectural Dimensions
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {categories.map((catKey) => {
          const scoreData = categoryScores ? categoryScores[catKey] : undefined;
          const isAvailable = categoryAvailability
            ? categoryAvailability[catKey] ?? false
            : false;

          const meta = CATEGORY_META[catKey] || {
            title: catKey,
            description: "",
            icon: <HelpCircle className="w-5 h-5 text-slate-400" />,
          };

          const hasScore = isAvailable && scoreData && scoreData.score !== null;
          const colors = getScoreColorClass(hasScore ? scoreData.score : null);

          return (
            <div
              key={catKey}
              className={`rounded-2xl p-5 border flex flex-col justify-between transition-all ${
                hasScore
                  ? `${colors.bg} ${colors.border}`
                  : "bg-slate-900/60 border-slate-800 text-slate-500"
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="p-2 rounded-xl bg-slate-900/80 border border-slate-800">
                    {meta.icon}
                  </div>
                  {hasScore ? (
                    <span className={`text-2xl font-black ${colors.text}`}>
                      {formatScore(scoreData.score)}
                    </span>
                  ) : (
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                      UNAVAILABLE
                    </span>
                  )}
                </div>

                <h4 className="font-semibold text-sm text-slate-200 mb-1">
                  {meta.title}
                </h4>
                <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                  {meta.description}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400 flex items-center justify-between">
                <span>Evaluated Checks:</span>
                <span className="font-mono text-slate-300 font-semibold">
                  {scoreData?.evaluatedChecks ?? 0}/{scoreData?.applicableChecks ?? 0}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
