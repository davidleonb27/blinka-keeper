/**
 * Generated from the FastAPI OpenAPI document (apps/api main:app, /api/v1/openapi.json) by
 * scripts/gen-api-schema.mjs. Do not edit: run `npm run gen:api`. ./scripts/check.sh fails when it is stale.
 */

export interface paths {
    "/api/v1/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_api_v1_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/workspaces": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Workspace */
        post: operations["create_workspace_api_v1_workspaces_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/workspaces/current": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Current Workspace */
        get: operations["current_workspace_api_v1_workspaces_current_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/onboarding/profile": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Propose Profile */
        post: operations["propose_profile_api_v1_onboarding_profile_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/onboarding/suppliers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Import Suppliers */
        post: operations["import_suppliers_api_v1_onboarding_suppliers_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/onboarding/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Complete */
        post: operations["complete_api_v1_onboarding_complete_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/policy": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Policy */
        get: operations["read_policy_api_v1_policy_get"];
        /** Apply Policy */
        put: operations["apply_policy_api_v1_policy_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/policy/compile": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Compile Policy */
        post: operations["compile_policy_api_v1_policy_compile_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/invoices": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Upload Invoice */
        post: operations["upload_invoice_api_v1_invoices_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/invoices/process": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Process Invoices */
        post: operations["process_invoices_api_v1_invoices_process_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/decisions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Decisions */
        get: operations["list_decisions_api_v1_decisions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/decisions/{invoice_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Acta */
        get: operations["read_acta_api_v1_decisions__invoice_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/decisions/{invoice_id}/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Approve */
        post: operations["approve_api_v1_decisions__invoice_id__approve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/decisions/{invoice_id}/reject": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reject */
        post: operations["reject_api_v1_decisions__invoice_id__reject_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/decisions/{invoice_id}/execute": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Execute Payment
         * @description Retries a payment whose execution failed. A payment that already went out is returned unchanged.
         */
        post: operations["execute_payment_api_v1_decisions__invoice_id__execute_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/decisions/{invoice_id}/narrative": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Narrative */
        get: operations["read_narrative_api_v1_decisions__invoice_id__narrative_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ledger": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Ledger */
        get: operations["read_ledger_api_v1_ledger_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ledger/verify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Verify Ledger */
        get: operations["verify_ledger_api_v1_ledger_verify_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ledger/tamper-demo": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Tamper Demo */
        post: operations["tamper_demo_api_v1_ledger_tamper_demo_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/trust": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Trust
         * @description Each supplier's earned auto-approval cap (R9), folded from its trust entries in the ledger.
         */
        get: operations["read_trust_api_v1_trust_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/trust/simulate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Simulate Month
         * @description Plays the demo's seeded month once, on the simulated rail. Calling it again changes nothing.
         */
        post: operations["simulate_month_api_v1_trust_simulate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/schedule": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Schedule
         * @description The next 45 days of approved payments: when each goes out, through which rail and why then.
         */
        get: operations["read_schedule_api_v1_schedule_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/schedule/run-due": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Run Due
         * @description Pays what is due today or earlier through the configured rail. Running it twice pays nothing twice.
         */
        post: operations["run_due_api_v1_schedule_run_due_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/reconciliations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Reconciliations */
        get: operations["list_reconciliations_api_v1_reconciliations_get"];
        put?: never;
        /**
         * Create Reconciliation
         * @description Reconciles a bank statement (CSV, PDF or image) or the demo statement against what this workspace paid.
         */
        post: operations["create_reconciliation_api_v1_reconciliations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/reconciliations/demo-statement": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Download Demo Statement
         * @description The demo statement, moved to the day this workspace paid its batch.
         */
        get: operations["download_demo_statement_api_v1_reconciliations_demo_statement_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/reconciliations/{reconciliation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Reconciliation */
        get: operations["read_reconciliation_api_v1_reconciliations__reconciliation_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/reconciliations/{reconciliation_id}/resolve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Resolve Movement
         * @description A person marks a movement that needed review as reviewed, with a note. It stays in the ledger.
         */
        post: operations["resolve_movement_api_v1_reconciliations__reconciliation_id__resolve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/periods/{period}/close": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Close Period
         * @description Closes the month once no outflow without an invoice is left unreviewed. Written to the ledger.
         */
        post: operations["close_period_api_v1_periods__period__close_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/periods/{period}/evidence.zip": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Download Evidence
         * @description The accountant's pack: summary PDF, reconciliation CSV, actas and the ledger with its verification.
         */
        get: operations["download_evidence_api_v1_periods__period__evidence_zip_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/redteam/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Start Run */
        post: operations["start_run_api_v1_redteam_runs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/challenge/attempts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Submit Attempt */
        post: operations["submit_attempt_api_v1_challenge_attempts_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/challenge/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Stats */
        get: operations["read_stats_api_v1_challenge_stats_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/firewall/intents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Submit Intent */
        post: operations["submit_intent_api_v1_firewall_intents_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** Acta */
        Acta: {
            decision: components["schemas"]["Decision"];
            invoice: components["schemas"]["InvoiceView"];
            /** Ledger */
            ledger: components["schemas"]["LedgerEntry"][];
        };
        /**
         * AgentVerdict
         * @enum {string}
         */
        AgentVerdict: "pay" | "hold" | "escalate";
        /** Agreement */
        "Agreement-Input": {
            kind: components["schemas"]["AgreementKind"];
            /** Amount */
            amount: number | string;
            /** Currency */
            currency: string;
            /** Tolerance Pct */
            tolerance_pct?: number | string | null;
            /** Source */
            source?: string | null;
            early_payment_discount?: components["schemas"]["EarlyPaymentDiscount-Input"] | null;
            /** Late Fee Pct */
            late_fee_pct?: number | string | null;
            /**
             * Critical
             * @default false
             */
            critical: boolean;
        };
        /** Agreement */
        "Agreement-Output": {
            kind: components["schemas"]["AgreementKind"];
            /** Amount */
            amount: number;
            /** Currency */
            currency: string;
            /** Tolerance Pct */
            tolerance_pct?: number | null;
            /** Source */
            source?: string | null;
            early_payment_discount?: components["schemas"]["EarlyPaymentDiscount-Output"] | null;
            /** Late Fee Pct */
            late_fee_pct?: number | null;
            /**
             * Critical
             * @default false
             */
            critical: boolean;
        };
        /**
         * AgreementKind
         * @enum {string}
         */
        AgreementKind: "fixed" | "monthly_cap";
        /** Approval */
        Approval: {
            /** Invoice Id */
            invoice_id: string;
            /**
             * Decision
             * @enum {string}
             */
            decision: "approved" | "rejected";
            /** Approver */
            approver: string;
            /**
             * Channel
             * @enum {string}
             */
            channel: "web" | "api";
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Note */
            note?: string | null;
        };
        /** ApprovalBody */
        ApprovalBody: {
            /** Approver */
            approver: string;
            /** Note */
            note?: string | null;
        };
        /** Approver */
        Approver: {
            /** Name */
            name: string;
            /** Role */
            role?: string | null;
            /** Email */
            email?: string | null;
        };
        /** AttackSpec */
        AttackSpec: {
            /** Round */
            round: number;
            /** Technique */
            technique: string;
            /** Rationale */
            rationale: string;
            /** Target Rules */
            target_rules: string[];
            /**
             * Render As
             * @enum {string}
             */
            render_as: "pdf" | "text" | "image";
            /** Invoice Text */
            invoice_text: string;
            /** Hidden Text */
            hidden_text?: string | null;
        };
        /** AuditFinding */
        AuditFinding: {
            /** Invoice Id */
            invoice_id: string;
            /**
             * Severity
             * @enum {string}
             */
            severity: "critical" | "warning";
            /** Message */
            message: string;
        };
        /** AuditReport */
        AuditReport: {
            /** Agrees */
            agrees: boolean;
            /** Checked */
            checked: number;
            /** Improper Payments */
            improper_payments: number;
            /**
             * Findings
             * @default []
             */
            findings: components["schemas"]["AuditFinding"][];
        };
        /** AutonomyDay */
        AutonomyDay: {
            /**
             * Day
             * Format: date
             */
            day: string;
            /** Decisions */
            decisions: number;
            /** Decided Alone */
            decided_alone: number;
            /** Rate */
            rate: number;
        };
        /** BalanceDay */
        BalanceDay: {
            /**
             * Day
             * Format: date
             */
            day: string;
            /** Balance */
            balance: number;
        };
        /** BatchResult */
        BatchResult: {
            /** Decisions */
            decisions: components["schemas"]["Decision"][];
            /** Spent Auto Base */
            spent_auto_base: number;
            /** Balance End */
            balance_end: number;
            metrics: components["schemas"]["Metrics"];
        };
        /** Beneficiary */
        "Beneficiary-Input": {
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Tax Id */
            tax_id: string;
            /**
             * Aliases
             * @default []
             */
            aliases: string[];
            /** Country */
            country?: string | null;
            /** Bank Name */
            bank_name: string;
            /** Account Number */
            account_number: string;
            /** Currency */
            currency: string;
            agreement?: components["schemas"]["Agreement-Input"] | null;
            /**
             * Allowed
             * @default true
             */
            allowed: boolean;
            /** Approver Contact */
            approver_contact?: string | null;
            /** Email Domain */
            email_domain?: string | null;
        };
        /** Beneficiary */
        "Beneficiary-Output": {
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Tax Id */
            tax_id: string;
            /**
             * Aliases
             * @default []
             */
            aliases: string[];
            /** Country */
            country?: string | null;
            /** Bank Name */
            bank_name: string;
            /** Account Number */
            account_number: string;
            /** Currency */
            currency: string;
            agreement?: components["schemas"]["Agreement-Output"] | null;
            /**
             * Allowed
             * @default true
             */
            allowed: boolean;
            /** Approver Contact */
            approver_contact?: string | null;
            /** Email Domain */
            email_domain?: string | null;
        };
        /** Body_create_reconciliation_api_v1_reconciliations_post */
        Body_create_reconciliation_api_v1_reconciliations_post: {
            /** File */
            file?: string | null;
            /**
             * Demo
             * @default false
             */
            demo: boolean;
            /** Fx Tolerance Pct */
            fx_tolerance_pct?: number | string | null;
        };
        /** Body_import_suppliers_api_v1_onboarding_suppliers_post */
        Body_import_suppliers_api_v1_onboarding_suppliers_post: {
            /** File */
            file: string;
        };
        /** Body_submit_attempt_api_v1_challenge_attempts_post */
        Body_submit_attempt_api_v1_challenge_attempts_post: {
            /** File */
            file?: string | null;
            /** Text */
            text?: string | null;
            /** Alias */
            alias?: string | null;
            /** Technique */
            technique?: string | null;
        };
        /** Body_upload_invoice_api_v1_invoices_post */
        Body_upload_invoice_api_v1_invoices_post: {
            /** File */
            file?: string | null;
            /** Text */
            text?: string | null;
        };
        /** CapturedThisMonth */
        CapturedThisMonth: {
            /** Year */
            year: number;
            /** Month */
            month: number;
            /** Discounts */
            discounts: number;
            /** Late Fees Avoided */
            late_fees_avoided: number;
            /** Treasury Yield */
            treasury_yield: number;
            /** Total */
            total: number;
            /** Payments */
            payments: number;
        };
        /** ChallengeAttempt */
        ChallengeAttempt: {
            /** Id */
            id: string;
            /** Alias */
            alias: string | null;
            /** Technique */
            technique: string | null;
            decision: components["schemas"]["Decision"];
            /** Broke Through */
            broke_through: boolean;
            /**
             * At
             * Format: date-time
             */
            at: string;
        };
        /** ChallengeStats */
        ChallengeStats: {
            /** Attempts */
            attempts: number;
            /** Improper Payments */
            improper_payments: number;
            /** Held */
            held: number;
            /** Escalated */
            escalated: number;
            /** Paid Legitimately */
            paid_legitimately: number;
            /**
             * Hall Of Fame
             * @default []
             */
            hall_of_fame: components["schemas"]["ChallengeAttempt"][];
        };
        /** CloseBody */
        CloseBody: {
            /** Closed By */
            closed_by: string;
        };
        /**
         * CompanyProfile
         * @description What Custodio infers about a company from its website and first answers, before asking anything else.
         */
        CompanyProfile: {
            /** Company Name */
            company_name: string;
            /** Website */
            website?: string | null;
            /** Industry */
            industry?: string | null;
            /** Country */
            country?: string | null;
            /**
             * Base Currency
             * @default USD
             */
            base_currency: string;
            /** Summary */
            summary?: string | null;
            /**
             * Likely Suppliers
             * @default []
             */
            likely_suppliers: string[];
            /** Suggested Rules Text */
            suggested_rules_text?: string | null;
            /**
             * Evidence Urls
             * @default []
             */
            evidence_urls: string[];
        };
        /** CompileRequest */
        CompileRequest: {
            /** Text */
            text: string;
            base?: components["schemas"]["Policy-Input"] | null;
        };
        /** CreateWorkspace */
        CreateWorkspace: {
            /** @default demo */
            mode: components["schemas"]["WorkspaceMode"];
        };
        /** Decision */
        Decision: {
            /** Invoice Id */
            invoice_id: string;
            /** Beneficiary Id */
            beneficiary_id: string | null;
            /** Supplier Name */
            supplier_name: string | null;
            /** Amount */
            amount: number | null;
            /** Currency */
            currency: string | null;
            /** Amount Base */
            amount_base: number | null;
            agent_verdict: components["schemas"]["AgentVerdict"];
            status: components["schemas"]["DecisionStatus"];
            /** Rules */
            rules: components["schemas"]["RuleResult"][];
            /** Explanation */
            explanation: string;
            /** Counterfactual */
            counterfactual: string | null;
            /** Narrative */
            narrative?: string | null;
            /** Balance Before */
            balance_before?: number | null;
            /** Balance After */
            balance_after?: number | null;
            approval?: components["schemas"]["Approval"] | null;
            /** Blocked Reason */
            blocked_reason?: string | null;
            execution?: components["schemas"]["PaymentExecution"] | null;
            trust?: components["schemas"]["TrustCap"] | null;
        };
        /**
         * DecisionItem
         * @description A row of the panel: the decision plus when and through which channel its invoice arrived.
         */
        DecisionItem: {
            decision: components["schemas"]["Decision"];
            /**
             * Received At
             * Format: date-time
             */
            received_at: string;
            source: components["schemas"]["InvoiceSource"];
            /** Invoice Number */
            invoice_number: string | null;
        };
        /**
         * DecisionStatus
         * @enum {string}
         */
        DecisionStatus: "paid_auto" | "paid_human" | "hold" | "pending_approval" | "rejected";
        /**
         * EarlyPaymentDiscount
         * @description Early-payment terms such as "2/10 net 30": `percent` off when paid within `days` of the issue date.
         */
        "EarlyPaymentDiscount-Input": {
            /** Percent */
            percent: number | string;
            /** Days */
            days: number;
        };
        /**
         * EarlyPaymentDiscount
         * @description Early-payment terms such as "2/10 net 30": `percent` off when paid within `days` of the issue date.
         */
        "EarlyPaymentDiscount-Output": {
            /** Percent */
            percent: number;
            /** Days */
            days: number;
        };
        /** Evidence */
        Evidence: {
            /** Quote */
            quote: string;
            /** Page */
            page?: number | null;
            /** Char Start */
            char_start?: number | null;
            /** Char End */
            char_end?: number | null;
        };
        /** ExtractedField */
        ExtractedField: {
            /** Value */
            value: string | null;
            evidence?: components["schemas"]["Evidence"] | null;
            /** Confidence */
            confidence: number;
            /**
             * Verified
             * @default false
             */
            verified: boolean;
        };
        /** ExtractedInvoice */
        ExtractedInvoice: {
            /** Document Id */
            document_id: string;
            source: components["schemas"]["InvoiceSource"];
            supplier_name: components["schemas"]["ExtractedField"];
            supplier_tax_id: components["schemas"]["ExtractedField"];
            invoice_number: components["schemas"]["ExtractedField"];
            issue_date: components["schemas"]["ExtractedField"];
            due_date: components["schemas"]["ExtractedField"];
            amount: components["schemas"]["ExtractedField"];
            currency: components["schemas"]["ExtractedField"];
            bank_name: components["schemas"]["ExtractedField"];
            account_number: components["schemas"]["ExtractedField"];
            description: components["schemas"]["ExtractedField"];
            /** Visible Text */
            visible_text: string;
            /** Sender Email */
            sender_email?: string | null;
            /**
             * Hidden Findings
             * @default []
             */
            hidden_findings: components["schemas"]["HiddenTextFinding"][];
            /** Reader */
            reader: string;
            /** Overall Confidence */
            overall_confidence: number;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** Health */
        Health: {
            /** Status */
            status: string;
            /** Version */
            version: string;
            /** Anthropic */
            anthropic: boolean;
            /**
             * Payment Rail
             * @enum {string}
             */
            payment_rail: "simulated" | "stripe_test" | "blinka_simulated";
            /** Sanctions List Date */
            sanctions_list_date?: string | null;
        };
        /** HiddenTextFinding */
        HiddenTextFinding: {
            kind: components["schemas"]["HiddenTextKind"];
            /** Text */
            text: string;
            /** Page */
            page?: number | null;
            /** Detail */
            detail: string;
        };
        /**
         * HiddenTextKind
         * @enum {string}
         */
        HiddenTextKind: "invisible_color" | "tiny_font" | "off_page" | "covered" | "metadata" | "instruction";
        /** IntentVerdict */
        IntentVerdict: {
            decision: components["schemas"]["Decision"];
            /** Ledger Hash */
            ledger_hash: string;
            /** Acta Url */
            acta_url: string;
        };
        /**
         * InvoiceSource
         * @enum {string}
         */
        InvoiceSource: "pdf" | "image" | "text" | "email" | "whatsapp" | "intent";
        /** InvoiceView */
        InvoiceView: {
            /** Id */
            id: string;
            /**
             * Received At
             * Format: date-time
             */
            received_at: string;
            /** Document Id */
            document_id: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "received" | "decided";
            /** Read Ok */
            read_ok: boolean;
            extraction: components["schemas"]["ExtractedInvoice"];
        };
        /** LedgerEntry */
        LedgerEntry: {
            /** Seq */
            seq: number;
            /**
             * At
             * Format: date-time
             */
            at: string;
            kind: components["schemas"]["LedgerKind"];
            /** Subject Id */
            subject_id: string | null;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /** Prev Hash */
            prev_hash: string;
            /** Hash */
            hash: string;
        };
        /**
         * LedgerKind
         * @enum {string}
         */
        LedgerKind: "policy_changed" | "invoice_received" | "decision" | "approval" | "payment" | "redteam_attack" | "challenge_attempt" | "intent" | "trust_raised" | "trust_revoked" | "simulation" | "reconciliation" | "reconciliation_review" | "period_closed";
        /** LedgerVerification */
        LedgerVerification: {
            /** Valid */
            valid: boolean;
            /** Length */
            length: number;
            /** First Broken Seq */
            first_broken_seq: number | null;
            /** Head Hash */
            head_hash: string | null;
        };
        /**
         * MatchLevel
         * @enum {string}
         */
        MatchLevel: "exact" | "amount_date" | "split" | "tolerance";
        /**
         * MatchSettings
         * @description Explicit and shown to the person: nothing is reconciled under a tolerance nobody can see.
         */
        MatchSettings: {
            /**
             * Date Window Days
             * @default 3
             */
            date_window_days: number;
            /**
             * Fx Tolerance Pct
             * @default 0.5
             */
            fx_tolerance_pct: number;
            /**
             * Max Split Parts
             * @default 4
             */
            max_split_parts: number;
        };
        /** Metrics */
        Metrics: {
            /** Total */
            total: number;
            /** Paid Auto */
            paid_auto: number;
            /** Paid Human */
            paid_human: number;
            /** Hold */
            hold: number;
            /** Pending */
            pending: number;
            /** Rejected */
            rejected: number;
            /** Autonomy Rate */
            autonomy_rate: number;
            /** Accuracy */
            accuracy?: number | null;
            /** Improper Payments */
            improper_payments: number;
        };
        /** MovementResult */
        MovementResult: {
            /** Movement Id */
            movement_id: string;
            status: components["schemas"]["MovementStatus"];
            level?: components["schemas"]["MatchLevel"] | null;
            /** Invoice Id */
            invoice_id?: string | null;
            /**
             * Allocated
             * @default 0
             */
            allocated: number;
            /** Difference */
            difference?: number | null;
            /** Duplicate Of */
            duplicate_of?: string | null;
            /** Reason */
            reason: string;
        };
        /**
         * MovementStatus
         * @enum {string}
         */
        MovementStatus: "reconciled" | "reconciled_with_difference" | "unmatched_outflow" | "bank_fee" | "duplicate" | "unread" | "inflow";
        /** MovementView */
        MovementView: {
            movement: components["schemas"]["StatementMovement"];
            result: components["schemas"]["MovementResult"];
            /** Needs Review */
            needs_review: boolean;
            review?: components["schemas"]["Review"] | null;
            /** Acta Url */
            acta_url?: string | null;
            /** External Id */
            external_id?: string | null;
            /** Dashboard Url */
            dashboard_url?: string | null;
        };
        /** Narrative */
        Narrative: {
            /** Invoice Id */
            invoice_id: string;
            /** Narrative */
            narrative: string;
        };
        /** OnboardingRequest */
        OnboardingRequest: {
            profile: components["schemas"]["CompanyProfile"];
            policy: components["schemas"]["Policy-Input"];
            /**
             * Suppliers
             * @default []
             */
            suppliers: components["schemas"]["Beneficiary-Input"][];
            /** Opening Balance */
            opening_balance: number | string;
            /** Fx Units Per Base */
            fx_units_per_base?: {
                [key: string]: number | string;
            } | null;
        };
        /** OnboardingResult */
        OnboardingResult: {
            workspace: components["schemas"]["WorkspaceSummary"];
            first_week: components["schemas"]["BatchResult"];
        };
        /** Outcome */
        Outcome: {
            batch: components["schemas"]["BatchResult"];
            audit: components["schemas"]["AuditReport"];
            /** Vetoed */
            vetoed: string[];
        };
        /**
         * PaymentExecution
         * @description What the payment rail did with a payment the engine decided. The rail executes; it never decides.
         */
        PaymentExecution: {
            /**
             * Rail
             * @enum {string}
             */
            rail: "simulated" | "stripe_test" | "blinka_simulated";
            /**
             * Status
             * @enum {string}
             */
            status: "executed" | "simulated" | "failed";
            /** External Id */
            external_id?: string | null;
            /** Dashboard Url */
            dashboard_url?: string | null;
            /**
             * Executed At
             * Format: date-time
             */
            executed_at: string;
            /** Error */
            error?: string | null;
            instruction?: components["schemas"]["PaymentInstruction"] | null;
        };
        /**
         * PaymentInstruction
         * @description Exactly what Custodio hands a bank partner (Blinka) to pay one invoice: original amount and currency.
         */
        PaymentInstruction: {
            /**
             * Network
             * @enum {string}
             */
            network: "ach" | "wire" | "bre_b" | "spei" | "pix";
            /** Amount */
            amount: number;
            /** Currency */
            currency: string;
            /** Beneficiary Name */
            beneficiary_name: string;
            /** Beneficiary Tax Id */
            beneficiary_tax_id: string;
            /** Beneficiary Country */
            beneficiary_country: string | null;
            /** Bank Name */
            bank_name: string;
            /** Account Number */
            account_number: string;
            /** Reference */
            reference: string;
            /** Idempotency Key */
            idempotency_key: string;
        };
        /** PaymentIntent */
        PaymentIntent: {
            /** Agent */
            agent: string;
            /** Beneficiary Name */
            beneficiary_name: string;
            /** Beneficiary Tax Id */
            beneficiary_tax_id?: string | null;
            /** Bank Name */
            bank_name?: string | null;
            /** Account Number */
            account_number: string;
            /** Amount */
            amount: number | string;
            /** Currency */
            currency: string;
            /** Invoice Number */
            invoice_number: string;
            /** Issue Date */
            issue_date?: string | null;
            /**
             * Description
             * @default
             */
            description: string;
            /** Document Text */
            document_text?: string | null;
        };
        /** PaymentResult */
        PaymentResult: {
            /** Invoice Id */
            invoice_id: string;
            /** Invoice Number */
            invoice_number: string | null;
            /** Supplier Name */
            supplier_name: string | null;
            /**
             * Paid On
             * Format: date
             */
            paid_on: string;
            /** Expected */
            expected: number | null;
            /** Currency */
            currency: string;
            status: components["schemas"]["PaymentStatus"];
            level?: components["schemas"]["MatchLevel"] | null;
            /** Movement Ids */
            movement_ids?: string[];
            /** Difference */
            difference?: number | null;
            /** External Id */
            external_id?: string | null;
            /** Dashboard Url */
            dashboard_url?: string | null;
            /** Acta Url */
            acta_url: string;
            /** Reason */
            reason: string;
        };
        /**
         * PaymentStatus
         * @enum {string}
         */
        PaymentStatus: "confirmed" | "pending";
        /** PeriodClose */
        PeriodClose: {
            /** Period */
            period: string;
            /**
             * Closed At
             * Format: date-time
             */
            closed_at: string;
            /** Closed By */
            closed_by: string;
            /** Reconciliation Id */
            reconciliation_id: string;
            /** Ledger Seq */
            ledger_seq: number;
            /** Ledger Hash */
            ledger_hash: string;
        };
        /** PeriodCloseView */
        PeriodCloseView: {
            close: components["schemas"]["PeriodClose"];
            summary: components["schemas"]["PeriodSummary"];
            /** Evidence Path */
            evidence_path: string;
        };
        /**
         * PeriodSummary
         * @description The month in figures, in the account's currency. `alerts_open` must be zero to close it.
         */
        PeriodSummary: {
            /** Currency */
            currency: string;
            paid: components["schemas"]["Tally"];
            held: components["schemas"]["Tally"];
            rejected: components["schemas"]["Tally"];
            pending_approval: components["schemas"]["Tally"];
            reconciled: components["schemas"]["Tally"];
            differences: components["schemas"]["Tally"];
            fees: components["schemas"]["Tally"];
            inflows: components["schemas"]["Tally"];
            unexplained: components["schemas"]["Tally"];
            pending_in_bank: components["schemas"]["Tally"];
            /** Alerts */
            alerts: number;
            /** Alerts Open */
            alerts_open: number;
        };
        /**
         * Policy
         * @description Everything a company decides. Amount thresholds are expressed in `base_currency`.
         */
        "Policy-Input": {
            /**
             * Version
             * @default 1
             */
            version: number;
            /**
             * Base Currency
             * @default USD
             */
            base_currency: string;
            /**
             * Approval Threshold
             * @default 5000
             */
            approval_threshold: number | string;
            /**
             * Per Payment Limit
             * @default 12000
             */
            per_payment_limit: number | string;
            /**
             * Period Budget
             * @default 37000
             */
            period_budget: number | string;
            /**
             * Reserve
             * @default 60000
             */
            reserve: number | string;
            /**
             * Agreement Tolerance Pct
             * @default 2
             */
            agreement_tolerance_pct: number | string;
            /**
             * Duplicate Window Days
             * @default 20
             */
            duplicate_window_days: number;
            /**
             * Split Window Days
             * @default 2
             */
            split_window_days: number;
            /**
             * Min Confidence
             * @default 0.9
             */
            min_confidence: number | string;
            /**
             * Allowed Currencies
             * @default [
             *       "USD",
             *       "COP",
             *       "MXN",
             *       "BRL",
             *       "CLP"
             *     ]
             */
            allowed_currencies: string[];
            /**
             * Beneficiaries
             * @default []
             */
            beneficiaries: components["schemas"]["Beneficiary-Input"][];
            /**
             * Approvers
             * @default []
             */
            approvers: components["schemas"]["Approver"][];
            /**
             * @default {
             *       "floor": 0,
             *       "hard_ceiling": false
             *     }
             */
            trust: components["schemas"]["TrustPolicy-Input"];
        };
        /**
         * Policy
         * @description Everything a company decides. Amount thresholds are expressed in `base_currency`.
         */
        "Policy-Output": {
            /**
             * Version
             * @default 1
             */
            version: number;
            /**
             * Base Currency
             * @default USD
             */
            base_currency: string;
            /**
             * Approval Threshold
             * @default 5000
             */
            approval_threshold: number;
            /**
             * Per Payment Limit
             * @default 12000
             */
            per_payment_limit: number;
            /**
             * Period Budget
             * @default 37000
             */
            period_budget: number;
            /**
             * Reserve
             * @default 60000
             */
            reserve: number;
            /**
             * Agreement Tolerance Pct
             * @default 2
             */
            agreement_tolerance_pct: number;
            /**
             * Duplicate Window Days
             * @default 20
             */
            duplicate_window_days: number;
            /**
             * Split Window Days
             * @default 2
             */
            split_window_days: number;
            /**
             * Min Confidence
             * @default 0.9
             */
            min_confidence: number;
            /**
             * Allowed Currencies
             * @default [
             *       "USD",
             *       "COP",
             *       "MXN",
             *       "BRL",
             *       "CLP"
             *     ]
             */
            allowed_currencies: string[];
            /**
             * Beneficiaries
             * @default []
             */
            beneficiaries: components["schemas"]["Beneficiary-Output"][];
            /**
             * Approvers
             * @default []
             */
            approvers: components["schemas"]["Approver"][];
            /**
             * @default {
             *       "floor": 0,
             *       "hard_ceiling": false
             *     }
             */
            trust: components["schemas"]["TrustPolicy-Output"];
        };
        /** PolicyChange */
        PolicyChange: {
            /** Field */
            field: string;
            /** Label */
            label: string;
            /** Before */
            before: unknown;
            /** After */
            after: unknown;
            /** Source Quote */
            source_quote: string;
        };
        /** PolicyProposal */
        PolicyProposal: {
            /** Text */
            text: string;
            /** Changes */
            changes: components["schemas"]["PolicyChange"][];
            /** Unsupported */
            unsupported: string[];
            /**
             * Questions
             * @default []
             */
            questions: string[];
            proposed: components["schemas"]["Policy-Output"];
            simulation?: components["schemas"]["SimulationReport"] | null;
        };
        /** ProfileRequest */
        ProfileRequest: {
            /** Company Name */
            company_name: string;
            /** Website */
            website?: string | null;
            /**
             * Answers
             * @default {}
             */
            answers: {
                [key: string]: string;
            };
        };
        /** ReconciliationItem */
        ReconciliationItem: {
            /** Id */
            id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Period */
            period: string;
            source: components["schemas"]["StatementSource"];
            /** Filename */
            filename: string;
            /** Movements */
            movements: number;
            /** Alerts Open */
            alerts_open: number;
            /** Period Closed */
            period_closed: boolean;
        };
        /** ReconciliationView */
        ReconciliationView: {
            /** Id */
            id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Period */
            period: string;
            source: components["schemas"]["StatementSource"];
            /** Filename */
            filename: string;
            /** Reader */
            reader: string;
            /** Currency */
            currency: string;
            /** Warnings */
            warnings: string[];
            /** Demo Shift Days */
            demo_shift_days: number | null;
            settings: components["schemas"]["MatchSettings"];
            /** Movements */
            movements: components["schemas"]["MovementView"][];
            /** Payments */
            payments: components["schemas"]["PaymentResult"][];
            summary: components["schemas"]["PeriodSummary"];
            /** Can Close */
            can_close: boolean;
            period_closed: components["schemas"]["PeriodClose"] | null;
            /** Ledger Seq */
            ledger_seq: number;
        };
        /** RedTeamEvent */
        RedTeamEvent: {
            /**
             * Type
             * @enum {string}
             */
            type: "round_started" | "attack_generated" | "verdict" | "round_finished" | "summary" | "error";
            /** Round */
            round: number;
            attack?: components["schemas"]["AttackSpec"] | null;
            decision?: components["schemas"]["Decision"] | null;
            /** Caught */
            caught?: boolean | null;
            /** Message */
            message?: string | null;
        };
        /** ResolveBody */
        ResolveBody: {
            /** Movement Id */
            movement_id: string;
            /** Reviewer */
            reviewer: string;
            /** Note */
            note: string;
        };
        /**
         * Review
         * @description A person looked at a movement that needed it and wrote down what it is. Stays in the ledger.
         */
        Review: {
            /** Movement Id */
            movement_id: string;
            /** Reviewer */
            reviewer: string;
            /** Note */
            note: string;
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Ledger Seq */
            ledger_seq: number;
        };
        /**
         * RuleOutcome
         * @enum {string}
         */
        RuleOutcome: "pass" | "hold" | "escalate" | "skipped";
        /** RuleResult */
        RuleResult: {
            /** Rule Id */
            rule_id: string;
            /** Key */
            key: string;
            /** Label */
            label: string;
            outcome: components["schemas"]["RuleOutcome"];
            /** Reason */
            reason: string;
            /**
             * Facts
             * @default {}
             */
            facts: {
                [key: string]: unknown;
            };
        };
        /** RunDue */
        RunDue: {
            /** Executed */
            executed: components["schemas"]["Decision"][];
            schedule: components["schemas"]["ScheduleView"];
        };
        /** RunRequest */
        RunRequest: {
            /**
             * Rounds
             * @default 6
             */
            rounds: number;
        };
        /** ScheduleView */
        ScheduleView: {
            /**
             * Today
             * Format: date
             */
            today: string;
            /** Horizon Days */
            horizon_days: number;
            /** Base Currency */
            base_currency: string;
            /** Rail */
            rail: string;
            /** Cash */
            cash: number;
            /** Committed Balance */
            committed_balance: number;
            /** Reserve */
            reserve: number;
            /** Apy */
            apy: number;
            /** Apy Note */
            apy_note: string;
            /** Items */
            items: components["schemas"]["ScheduledItem"][];
            /** Waiting */
            waiting: components["schemas"]["ScheduledItem"][];
            /** Balance */
            balance: components["schemas"]["BalanceDay"][];
            captured: components["schemas"]["CapturedThisMonth"];
        };
        /** ScheduledItem */
        ScheduledItem: {
            /** Invoice Id */
            invoice_id: string;
            /** Beneficiary Id */
            beneficiary_id: string | null;
            /** Supplier Name */
            supplier_name: string;
            /** Amount */
            amount: number | null;
            /** Currency */
            currency: string | null;
            /** Amount Base */
            amount_base: number;
            /** Due Date */
            due_date: string | null;
            /** Pay On */
            pay_on: string | null;
            timing: components["schemas"]["Timing"];
            /** Reason */
            reason: string;
            /** Rail */
            rail: string;
            /** Discount Base */
            discount_base: number;
            /** Late Fee Avoided Base */
            late_fee_avoided_base: number;
            /** Yield Base */
            yield_base: number;
        };
        /** SimulatedChange */
        SimulatedChange: {
            /** Invoice Id */
            invoice_id: string;
            /** Supplier Name */
            supplier_name: string | null;
            before: components["schemas"]["DecisionStatus"];
            after: components["schemas"]["DecisionStatus"];
            /** Reason */
            reason: string;
        };
        /** SimulationReport */
        SimulationReport: {
            before: components["schemas"]["Metrics"];
            after: components["schemas"]["Metrics"];
            /** Changed */
            changed: components["schemas"]["SimulatedChange"][];
        };
        /** SimulationResult */
        SimulationResult: {
            /** Created */
            created: boolean;
            /** Seed */
            seed: number;
            /**
             * Start
             * Format: date
             */
            start: string;
            /** Days */
            days: number;
            /** Invoices */
            invoices: number;
            /** Inflow Base */
            inflow_base: number;
            trust: components["schemas"]["TrustOverview"];
        };
        /** StatementMovement */
        StatementMovement: {
            /** Id */
            id: string;
            /** Row */
            row: number;
            /** Booked On */
            booked_on: string | null;
            /** Description */
            description: string;
            /** Amount */
            amount: number | null;
            /** Currency */
            currency: string | null;
            /** Reference */
            reference?: string | null;
            /** Quote */
            quote: string;
            /** Read */
            read: boolean;
            /** Unread Reason */
            unread_reason?: string | null;
        };
        /**
         * StatementSource
         * @enum {string}
         */
        StatementSource: "csv" | "document" | "demo";
        /** SupplierImport */
        SupplierImport: {
            /** Beneficiaries */
            beneficiaries: components["schemas"]["Beneficiary-Output"][];
            /**
             * Warnings
             * @default []
             */
            warnings: string[];
        };
        /** SupplierTrust */
        SupplierTrust: {
            /** Beneficiary Id */
            beneficiary_id: string;
            /** Supplier Name */
            supplier_name: string;
            /** Has History */
            has_history: boolean;
            /** Cap */
            cap: number;
            /** Clean Streak */
            clean_streak: number;
            /** Supervised */
            supervised: boolean;
            /** Reason */
            reason: string;
            /** Clean Needed */
            clean_needed: number;
            /** Next Cap */
            next_cap: number | null;
            last_incident: components["schemas"]["TrustStep"] | null;
            /** Timeline */
            timeline: components["schemas"]["TrustStep"][];
        };
        /** Tally */
        Tally: {
            /**
             * Count
             * @default 0
             */
            count: number;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** TamperDemo */
        TamperDemo: {
            /** Altered Seq */
            altered_seq: number;
            /** Altered Field */
            altered_field: string;
            tampered: components["schemas"]["LedgerVerification"];
            real: components["schemas"]["LedgerVerification"];
        };
        /** TamperRequest */
        TamperRequest: {
            /** Seq */
            seq?: number | null;
        };
        /**
         * Timing
         * @enum {string}
         */
        Timing: "discount" | "on_due" | "overdue" | "no_due_date" | "short_of_cash";
        /**
         * TrustCap
         * @description The auto-approval cap (R9) one supplier has earned, folded from its trust entries in the ledger.
         */
        TrustCap: {
            /** Beneficiary Id */
            beneficiary_id: string;
            /** Cap */
            cap: number;
            /** Clean Streak */
            clean_streak: number;
            /** Supervised */
            supervised: boolean;
            /** Reason */
            reason: string;
        };
        /** TrustOverview */
        TrustOverview: {
            /** Base Currency */
            base_currency: string;
            /** Autonomy Rate */
            autonomy_rate: number;
            /** Floor */
            floor: number;
            /** Ceiling */
            ceiling: number;
            /** Policy Threshold */
            policy_threshold: number;
            /** Hard Ceiling */
            hard_ceiling: boolean;
            /** Clean Payments To Earn */
            clean_payments_to_earn: number;
            /** Suppliers */
            suppliers: components["schemas"]["SupplierTrust"][];
            /** Autonomy */
            autonomy: components["schemas"]["AutonomyDay"][];
        };
        /**
         * TrustPolicy
         * @description How a supplier earns a higher auto-approval cap (R9). See custodio.engine.trust for the formula.
         */
        "TrustPolicy-Input": {
            /**
             * Floor
             * @default 0
             */
            floor: number | string;
            /**
             * Hard Ceiling
             * @default false
             */
            hard_ceiling: boolean;
        };
        /**
         * TrustPolicy
         * @description How a supplier earns a higher auto-approval cap (R9). See custodio.engine.trust for the formula.
         */
        "TrustPolicy-Output": {
            /**
             * Floor
             * @default 0
             */
            floor: number;
            /**
             * Hard Ceiling
             * @default false
             */
            hard_ceiling: boolean;
        };
        /**
         * TrustStep
         * @description One entry of a supplier's trust history, as the ledger holds it.
         */
        TrustStep: {
            /** Seq */
            seq: number;
            /**
             * At
             * Format: date-time
             */
            at: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "trust_raised" | "trust_revoked";
            /** Invoice Id */
            invoice_id: string;
            /** Rule Id */
            rule_id: string | null;
            /** Reason */
            reason: string;
            /** Summary */
            summary: string;
            /** Cap Before */
            cap_before: number | null;
            /** Cap After */
            cap_after: number | null;
            /** Clean Streak */
            clean_streak: number | null;
            /** Hash */
            hash: string;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /** WorkspaceCreated */
        WorkspaceCreated: {
            /** Workspace Id */
            workspace_id: string;
            /** Api Key */
            api_key: string;
        };
        /**
         * WorkspaceMode
         * @enum {string}
         */
        WorkspaceMode: "demo" | "blank";
        /** WorkspaceSummary */
        WorkspaceSummary: {
            /** Workspace Id */
            workspace_id: string;
            /** Company Name */
            company_name: string;
            /**
             * Today
             * Format: date
             */
            today: string;
            /** Base Currency */
            base_currency: string;
            /** Opening Balance */
            opening_balance: number;
            /** Balance */
            balance: number;
            /** Spent Auto Base */
            spent_auto_base: number;
            /** Reserve */
            reserve: number;
            /** Period Budget */
            period_budget: number;
            /** Policy Version */
            policy_version: number;
            /** Pending Invoices */
            pending_invoices: number;
            metrics: components["schemas"]["Metrics"];
            audit: components["schemas"]["AuditReport"];
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    health_api_v1_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Health"];
                };
            };
        };
    };
    create_workspace_api_v1_workspaces_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateWorkspace"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkspaceCreated"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    current_workspace_api_v1_workspaces_current_get: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkspaceSummary"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    propose_profile_api_v1_onboarding_profile_post: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProfileRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CompanyProfile"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    import_suppliers_api_v1_onboarding_suppliers_post: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_import_suppliers_api_v1_onboarding_suppliers_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SupplierImport"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    complete_api_v1_onboarding_complete_post: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OnboardingRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OnboardingResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_policy_api_v1_policy_get: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Policy-Output"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    apply_policy_api_v1_policy_put: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Policy-Input"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Policy-Output"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    compile_policy_api_v1_policy_compile_post: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CompileRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PolicyProposal"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    upload_invoice_api_v1_invoices_post: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "multipart/form-data": components["schemas"]["Body_upload_invoice_api_v1_invoices_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InvoiceView"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    process_invoices_api_v1_invoices_process_post: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Outcome"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_decisions_api_v1_decisions_get: {
        parameters: {
            query?: {
                status?: components["schemas"]["DecisionStatus"] | null;
            };
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DecisionItem"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_acta_api_v1_decisions__invoice_id__get: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path: {
                invoice_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Acta"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    approve_api_v1_decisions__invoice_id__approve_post: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path: {
                invoice_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ApprovalBody"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Decision"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reject_api_v1_decisions__invoice_id__reject_post: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path: {
                invoice_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ApprovalBody"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Decision"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    execute_payment_api_v1_decisions__invoice_id__execute_post: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path: {
                invoice_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Decision"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_narrative_api_v1_decisions__invoice_id__narrative_get: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path: {
                invoice_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Narrative"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_ledger_api_v1_ledger_get: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LedgerEntry"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    verify_ledger_api_v1_ledger_verify_get: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LedgerVerification"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    tamper_demo_api_v1_ledger_tamper_demo_post: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TamperRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TamperDemo"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_trust_api_v1_trust_get: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TrustOverview"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    simulate_month_api_v1_trust_simulate_post: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SimulationResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_schedule_api_v1_schedule_get: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScheduleView"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    run_due_api_v1_schedule_run_due_post: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RunDue"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_reconciliations_api_v1_reconciliations_get: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReconciliationItem"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_reconciliation_api_v1_reconciliations_post: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "multipart/form-data": components["schemas"]["Body_create_reconciliation_api_v1_reconciliations_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReconciliationView"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    download_demo_statement_api_v1_reconciliations_demo_statement_get: {
        parameters: {
            query?: {
                format?: "csv" | "pdf";
            };
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "text/csv": unknown;
                    "application/pdf": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_reconciliation_api_v1_reconciliations__reconciliation_id__get: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path: {
                reconciliation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReconciliationView"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    resolve_movement_api_v1_reconciliations__reconciliation_id__resolve_post: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path: {
                reconciliation_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ResolveBody"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReconciliationView"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    close_period_api_v1_periods__period__close_post: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path: {
                /** @description yyyy-mm */
                period: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CloseBody"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PeriodCloseView"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    download_evidence_api_v1_periods__period__evidence_zip_get: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path: {
                /** @description yyyy-mm */
                period: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/zip": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    start_run_api_v1_redteam_runs_post: {
        parameters: {
            query?: never;
            header?: {
                "x-custodio-workspace"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RunRequest"];
            };
        };
        responses: {
            /** @description Server-sent events; each `data:` line is a RedTeamEvent. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "text/event-stream": components["schemas"]["RedTeamEvent"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    submit_attempt_api_v1_challenge_attempts_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "multipart/form-data": components["schemas"]["Body_submit_attempt_api_v1_challenge_attempts_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ChallengeAttempt"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_stats_api_v1_challenge_stats_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ChallengeStats"];
                };
            };
        };
    };
    submit_intent_api_v1_firewall_intents_post: {
        parameters: {
            query?: never;
            header?: {
                authorization?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PaymentIntent"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IntentVerdict"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
