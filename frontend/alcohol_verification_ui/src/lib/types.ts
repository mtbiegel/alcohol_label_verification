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
  overridden?: boolean;
}

export interface VerificationResult {
  overallStatus: 'approved' | 'rejected' | 'review';
  fields: FieldResult[];
  summary: string;
}

export interface FilePair {
  baseName: string;
  imageFile: File | null;
  applicationFile: File | null;
  applicationData: ApplicationData | null;
  status: 'complete' | 'missing-image' | 'missing-application';
  result?: VerificationResult;
}

export interface VerificationBatch {
  id: string;
  timestamp: Date;
  pairs: FilePair[];
}