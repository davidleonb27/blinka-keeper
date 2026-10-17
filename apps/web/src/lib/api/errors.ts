/** Typed API failures. Every message is Spanish and safe to show to a person as is. */

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
  ) {
    super(message);
    this.name = new.target.name;
  }
}

export class RateLimitedError extends ApiError {
  constructor() {
    super("Vas muy rápido. Espera un minuto y vuelve a intentarlo.", 429);
  }
}

export class ServiceUnavailableError extends ApiError {
  constructor(detail: string | null) {
    super(
      detail ??
        "El servicio de lectura no está disponible ahora. Nada se pagó: queda para revisión humana.",
      503,
    );
  }
}

export class NotFoundError extends ApiError {
  constructor() {
    super("No encontramos eso en tu espacio de trabajo.", 404);
  }
}

export class PayloadTooLargeError extends ApiError {
  constructor() {
    super("El archivo pesa más de 4 MB. Prueba con uno más liviano.", 413);
  }
}

export class InvalidRequestError extends ApiError {
  constructor(detail: string | null, status: number) {
    super(detail ?? "Revisa los datos: hay algo que Custodio no pudo aceptar.", status);
  }
}

export class NetworkError extends ApiError {
  constructor() {
    super("No pudimos conectarnos con Custodio. Revisa tu conexión y vuelve a intentarlo.", null);
  }
}

export class UnexpectedResponseError extends ApiError {
  constructor(status: number) {
    super("Custodio respondió algo inesperado. Nada se pagó; vuelve a intentarlo.", status);
  }
}

export function errorFromStatus(status: number, detail: string | null): ApiError {
  switch (status) {
    case 404:
      return new NotFoundError();
    case 413:
      return new PayloadTooLargeError();
    case 429:
      return new RateLimitedError();
    case 503:
      return new ServiceUnavailableError(detail);
    default:
      return status >= 400 && status < 500
        ? new InvalidRequestError(detail, status)
        : new UnexpectedResponseError(status);
  }
}

export function messageOf(error: unknown): string {
  return error instanceof ApiError ? error.message : new UnexpectedResponseError(0).message;
}
