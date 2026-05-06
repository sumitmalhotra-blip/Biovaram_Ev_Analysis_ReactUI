declare module "utif" {
  interface IFD {
    width: number;
    height: number;
    [key: string]: unknown;
  }

  function decode(buffer: ArrayBuffer): IFD[];
  function decodeImage(buffer: ArrayBuffer, ifd: IFD): void;
  function toRGBA8(ifd: IFD): Uint8Array;

  export { decode, decodeImage, toRGBA8 };
  export type { IFD };
}