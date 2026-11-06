import * as yup from 'yup'

/**
 * Validation schema for the "Register New User" (client onboarding) form.
 * Built via a factory so error messages stay in sync with the active i18n locale.
 *
 * @param {(key: string, params?: object) => string} t vue-i18n translate fn
 */
export function createRegisterSchema(t) {
  return yup.object({
    first_name: yup
      .string()
      .trim()
      .required(t('validation.required')),
    last_name: yup
      .string()
      .trim()
      .required(t('validation.required')),
    exchange_name: yup
      .string()
      .trim()
      .required(t('validation.required')),
    country: yup
      .string()
      .trim()
      .required(t('validation.required')),
    email: yup
      .string()
      .trim()
      .email(t('validation.emailInvalid'))
      .required(t('validation.required')),
    phone: yup
      .string()
      .trim()
      .required(t('validation.required'))
      .matches(
        /^[+()\-\s\d]{6,20}$/,
        t('validation.phoneInvalid')
      ),
    website: yup
      .string()
      .trim()
      .url(t('validation.urlInvalid'))
      .nullable()
      .transform((value) => (value ? value : null))
      .default(null),
    collaboration_type: yup.string(),
    telegram_id: yup.string(),
    telegram_username: yup.string(),
    sub_role: yup.string().default('admin'),
    owner_username: yup
      .string()
      .trim()
      .when('sub_role', {
        is: (value) => value === 'operator' || value === 'head_operator',
        then: (schema) => schema.required(t('programmerHub.ownerUsernameRequired')),
        otherwise: (schema) => schema.notRequired(),
      }),
    telegram_bot_token: yup
      .string()
      .trim()
      .when('sub_role', {
        // Delegated operators don't own a bot, so no token is needed for them.
        is: (value) => value === 'operator' || value === 'head_operator',
        then: (schema) => schema.notRequired(),
        otherwise: (schema) => schema.required(t('telegram.botSetup.tokenRequired')),
      }),
    plan: yup.string().required(),
  })
}

/** Touched-field error extraction helper (first error per field). */
export function collectFieldErrors(schema, values, touched) {
  try {
    schema.validateSync(values, { abortEarly: false })
    return {}
  } catch (err) {
    if (!err?.inner) return {}
    const errors = {}
    for (const item of err.inner) {
      const path = item.path
      if (!path) continue
      if (touched[path] && !errors[path]) errors[path] = item.message
    }
    return errors
  }
}
