import React from 'react';
export const Comp = ({ html }: { html: string }) => (
  <div dangerouslySetInnerHTML={{ __html: html }} />
);
