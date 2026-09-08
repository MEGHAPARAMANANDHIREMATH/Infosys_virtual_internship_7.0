import { useState } from 'react';

export function useFormState(initial) {
  const [values, setValues] = useState(initial);
  const update = (field, value) => setValues((prev) => ({ ...prev, [field]: value }));
  const reset = () => setValues(initial);
  return { values, update, reset, setValues };
}
