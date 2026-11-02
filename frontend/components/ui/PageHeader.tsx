"use client";

import React from "react";

interface PageHeaderProps {
  title: string;
  description?: string;
  eyebrow?: string;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  description,
  eyebrow,
  badge,
  actions,
  className = "",
}: PageHeaderProps) {
  return (
    <div className={`page-header ${className}`}>
      <div className="page-header-content">
        {eyebrow && <span className="page-header-eyebrow">{eyebrow}</span>}
        <div className="page-header-title-row">
          <h1 className="page-header-title">{title}</h1>
          {badge && <div className="page-header-badge">{badge}</div>}
        </div>
        {description && <p className="page-header-desc">{description}</p>}
      </div>
      {actions && <div className="page-header-actions">{actions}</div>}
    </div>
  );
}
