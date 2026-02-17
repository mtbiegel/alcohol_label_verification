export interface ApplicationData {
  brand_name: string;
  class_type: string;
  alcohol_content_amount: string;
  alcohol_content_format: string;
  net_contents_amount: string;
  net_contents_unit: string;
  producer_name: string;
  country_of_origin: string;
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