function output_img = process_line(input_img)
    % input_img moet een RGB uint8 image zijn
    gray = rgb2gray(input_img);

    % Binariseer voor zwarte lijn
    bw = imbinarize(gray, 'adaptive', 'ForegroundPolarity', 'dark', 'Sensitivity', 0.4);

    % Zoek lijnen
    [H,theta,rho] = hough(bw);
    peaks = houghpeaks(H,5);
    lines = houghlines(bw,theta,rho,peaks);

    output_img = input_img;
    paarse_kleur = [128, 0, 128];

    for k = 1:length(lines)
        xy = [lines(k).point1; lines(k).point2];
        output_img = draw_paarse_lijn(output_img, xy, paarse_kleur, 3); % helper functie
    end
end

function img = draw_paarse_lijn(img, xy, kleur, width)
    % Teken een paarse lijn op een rgb image met Bresenham (of linspace)
    % xy: 2x2 matrix met [x1 y1; x2 y2]
    x1 = xy(1,1); y1 = xy(1,2);
    x2 = xy(2,1); y2 = xy(2,2);
    n = max(abs([x2-x1, y2-y1]))+1;
    x = round(linspace(x1, x2, n));
    y = round(linspace(y1, y2, n));
    for i = 1:length(x)
        for dx = -floor(width/2):floor(width/2)
            for dy = -floor(width/2):floor(width/2)
                xi = x(i)+dx;
                yi = y(i)+dy;
                if xi>0 && yi>0 && xi<=size(img,2) && yi<=size(img,1)
                    img(yi, xi, 1) = kleur(1);
                    img(yi, xi, 2) = kleur(2);
                    img(yi, xi, 3) = kleur(3);
                end
            end
        end
    end
end
