export interface ApplicationData {
  brand_name: string;
  class_type: string;
  alcohol_content: string;
  net_contents: string;
  producer_name: string;
  country_of_origin: string;
  gov_warning: string;
}

export interface FieldResult {
  field: string;
  extracted: string;
  expected: string;
  status: 'pass' | 'fail' | 'warning';
  note?: string;
}

export interface VerificationResult {
  overallStatus: 'approved' | 'rejected' | 'review';
  fields: FieldResult[];
  summary: string;
}