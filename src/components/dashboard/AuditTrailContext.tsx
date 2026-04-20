import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";

export type AuditActionType = "override" | "review_request" | "discrepancy_report";

export interface AuditAction {
  id: string;
  type: AuditActionType;
  timestamp: string;
  tokenId: string;
  reason: string;
  rootHash: string;
}

interface AuditTrailContextType {
  actions: AuditAction[];
  recordAction: (type: AuditActionType, tokenId: string, reason: string, rootHash: string) => void;
  latestRootHash: string;
}

const AuditTrailContext = createContext<AuditTrailContextType | undefined>(undefined);

export const AuditTrailProvider: React.FC<{ children: ReactNode; initialRootHash: string }> = ({ children, initialRootHash }) => {
  const [actions, setActions] = useState<AuditAction[]>([]);
  const [latestRootHash, setLatestRootHash] = useState(initialRootHash);

  // Load from localStorage on mount
  useEffect(() => {
    const savedActions = localStorage.getItem("grid-ledger-audit-trail");
    if (savedActions) {
      try {
        const parsed = JSON.parse(savedActions);
        setActions(parsed);
        if (parsed.length > 0) {
          setLatestRootHash(parsed[0].rootHash);
        }
      } catch (e) {
        console.error("Failed to parse audit trail", e);
      }
    }
  }, []);

  const recordAction = (type: AuditActionType, tokenId: string, reason: string, rootHash: string) => {
    // In a real system, the rootHash would be recalculated here. 
    // For this implementation, we'll use the provided rootHash as the "anchor".
    const newAction: AuditAction = {
      id: Math.random().toString(36).substring(2, 9),
      type,
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
      tokenId,
      reason,
      rootHash,
    };

    const updatedActions = [newAction, ...actions];
    setActions(updatedActions);
    setLatestRootHash(rootHash);
    localStorage.setItem("grid-ledger-audit-trail", JSON.stringify(updatedActions));
  };

  return (
    <AuditTrailContext.Provider value={{ actions, recordAction, latestRootHash }}>
      {children}
    </AuditTrailContext.Provider>
  );
};

export const useAuditTrail = () => {
  const context = useContext(AuditTrailContext);
  if (context === undefined) {
    throw new Error("useAuditTrail must be used within an AuditTrailProvider");
  }
  return context;
};
