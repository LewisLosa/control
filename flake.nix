{
  description = "SengozHome control dashboard and application workers";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs = {self, nixpkgs}: let
    systems = ["x86_64-linux" "aarch64-linux" "aarch64-darwin"];
    forAllSystems = nixpkgs.lib.genAttrs systems;
  in {
    packages = forAllSystems (system: let
      pkgs = import nixpkgs {inherit system;};
      inherit (pkgs) lib;
      node = pkgs.nodejs_22;
      pnpm = pkgs.pnpm_10;

      backend = pkgs.stdenvNoCC.mkDerivation {
        pname = "control-backend";
        version = "0.1.0";
        src = ./.;
        dontBuild = true;
        installPhase = ''
          mkdir -p $out/lib
          cp -r backend $out/lib/backend
        '';
      };

      av1-assets = pkgs.stdenvNoCC.mkDerivation {
        pname = "control-av1-assets";
        version = "0.1.0";
        src = ./backend/av1/assets;
        dontBuild = true;
        installPhase = ''
          mkdir -p $out
          cp -r . $out/
        '';
      };

      pythonApp = module: pkgs.writeShellApplication {
        name = lib.last (lib.splitString "." module);
        runtimeInputs = [pkgs.python3];
        text = ''
          export PYTHONPATH=${backend}/lib''${PYTHONPATH:+:$PYTHONPATH}
          exec ${pkgs.python3}/bin/python3 -m ${module} "$@"
        '';
      };
    in {
      control-web = pkgs.stdenvNoCC.mkDerivation (finalAttrs: {
        pname = "control-web";
        version = "0.1.0";
        src = ./.;
        nativeBuildInputs = [node pnpm pkgs.pnpmConfigHook];
        pnpmDeps = pkgs.fetchPnpmDeps {
          inherit (finalAttrs) pname version src;
          inherit pnpm;
          fetcherVersion = 4;
          hash = "sha256-CbAlAhIDq+F6/iXKUa/Wr6c9OuKtePk3P5T/eppUlA4=";
        };
        buildPhase = ''
          runHook preBuild
          pnpm run build
          runHook postBuild
        '';
        installPhase = ''
          mkdir -p $out
          cp -r build $out/build
        '';
      });

      music-worker = pythonApp "backend.music.worker";
      music-web = pythonApp "backend.music.web";
      av1-worker = pythonApp "backend.av1.worker";
      av1-web = pythonApp "backend.av1.web";
      av1-enqueue = pythonApp "backend.av1.enqueue";
      av1-encode = pythonApp "backend.av1.direct";
      av1-assets = av1-assets;
      arr-auto-import = pythonApp "backend.arr.auto_import";
      music-library-sanitize = pythonApp "backend.music.library_sanitize";
    });
  };
}
